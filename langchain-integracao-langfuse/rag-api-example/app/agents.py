import asyncio
import logging
import re
import time
import uuid

from langfuse import get_client as get_langfuse
from langfuse import observe, propagate_attributes

from . import config
from .llm import get_client
from .retrieval import search
from .schemas import RunAgentsResponse, ScoredAnswer

logger = logging.getLogger("rag.agents")

GENERATOR_SYSTEM = (
    "Você é um assistente objetivo. Responda em português usando APENAS o contexto fornecido. "
    "Se o contexto não contiver a resposta, diga que não encontrou a informação."
)

EVALUATOR_SYSTEM = (
    "Você é um avaliador rigoroso. Dados um contexto, uma pergunta e uma resposta candidata, "
    "avalie correção, fidelidade ao contexto e clareza. Responda APENAS com um número de 0 a 10 "
    "(pode ter casas decimais), sem nenhum outro texto."
)

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def format_context(trechos: list[tuple[str, str]]) -> str:
    return "\n\n".join(f"[{source}] {content}" for source, content in trechos)


async def generate_answer(pergunta: str, contexto: str) -> str:
    """Agente gerador: uma chamada ao servidor OpenAI-compatível."""
    completion = await get_client().chat.completions.create(
        name="generate-answer",
        model=config.LLM_MODEL,
        temperature=1.0,
        messages=[
            {"role": "system", "content": GENERATOR_SYSTEM},
            {"role": "user", "content": f"Contexto:\n{contexto}\n\nPergunta:\n{pergunta}"},
        ],
    )
    return (completion.choices[0].message.content or "").strip()


@observe(as_type="agent", name="generate-answers", capture_input=False, capture_output=False)
async def generate_answers(pergunta: str, contexto: str, n: int) -> list[str]:
    get_langfuse().update_current_span(input={"pergunta": pergunta, "num_candidates": n})
    # n chamadas independentes: nem todo servidor local suporta o parâmetro `n`
    logger.info("Agente gerador: solicitando %d respostas ao servidor OpenAI", n)
    start = time.perf_counter()
    respostas = list(await asyncio.gather(*(generate_answer(pergunta, contexto) for _ in range(n))))
    logger.info("Agente gerador: %d respostas recebidas em %.0f ms", len(respostas), (time.perf_counter() - start) * 1000)
    get_langfuse().update_current_span(output=respostas)
    return respostas


def parse_score(text: str) -> float:
    match = _NUMBER.search(text or "")
    if not match:
        return 0.0
    return min(10.0, max(0.0, float(match.group().replace(",", "."))))


@observe(as_type="evaluator", name="evaluate-answer", capture_input=False, capture_output=False)
async def evaluate_answer(pergunta: str, resposta: str, contexto: str) -> float:
    """Agente avaliador: devolve o score (0-10) de uma resposta."""
    get_langfuse().update_current_span(input={"pergunta": pergunta, "resposta": resposta})
    completion = await get_client().chat.completions.create(
        name="score-answer",
        model=config.LLM_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": EVALUATOR_SYSTEM},
            {
                "role": "user",
                "content": f"Contexto:\n{contexto}\n\nPergunta:\n{pergunta}\n\nResposta:\n{resposta}",
            },
        ],
    )
    score = parse_score(completion.choices[0].message.content or "")
    langfuse = get_langfuse()
    langfuse.update_current_span(output={"score": score})
    langfuse.score_current_span(name="answer-score", value=score, data_type="NUMERIC")
    return score


@observe(as_type="agent", name="evaluate-answers", capture_input=False, capture_output=False)
async def evaluate_answers(pergunta: str, respostas: list[str], contexto: str) -> list[float]:
    get_langfuse().update_current_span(input={"pergunta": pergunta, "respostas": respostas})
    logger.info("Agente avaliador: avaliando %d respostas", len(respostas))
    scores = list(await asyncio.gather(*(evaluate_answer(pergunta, r, contexto) for r in respostas)))
    logger.info("Agente avaliador: scores=%s", scores)
    get_langfuse().update_current_span(output={"scores": scores})
    return scores


@observe(name="select-best-answer", capture_input=False, capture_output=False)
def select_best_answer(candidatas: list[ScoredAnswer]) -> ScoredAnswer | None:
    langfuse = get_langfuse()
    langfuse.update_current_span(
        input=[{"resposta": c.resposta, "score": c.score} for c in candidatas],
        metadata={"score_threshold": config.SCORE_THRESHOLD},
    )
    elegiveis = [c for c in candidatas if c.elegivel]
    melhor = max(elegiveis, key=lambda c: c.score) if elegiveis else None

    if melhor:
        logger.info(
            "Melhor resposta eleita score=%.1f (%d elegíveis de %d, limiar>%.1f)",
            melhor.score, len(elegiveis), len(candidatas), config.SCORE_THRESHOLD,
        )
    else:
        logger.warning("Nenhuma resposta elegível (limiar>%.1f)", config.SCORE_THRESHOLD)

    langfuse.update_current_span(
        output=melhor.resposta if melhor else None,
        metadata={"score_threshold": config.SCORE_THRESHOLD, "elegiveis": len(elegiveis)},
    )
    return melhor


async def _run_pipeline(pergunta: str) -> RunAgentsResponse:
    trechos = await search(pergunta, config.TOP_K)
    contexto = format_context(trechos)
    respostas = await generate_answers(pergunta, contexto, config.NUM_CANDIDATES)
    scores = await evaluate_answers(pergunta, respostas, contexto)

    candidatas = [
        ScoredAnswer(resposta=r, score=s, elegivel=s > config.SCORE_THRESHOLD)
        for r, s in zip(respostas, scores)
    ]
    melhor = select_best_answer(candidatas)

    return RunAgentsResponse(
        pergunta=pergunta,
        resposta=melhor.resposta if melhor else None,
        score=melhor.score if melhor else None,
        fontes=sorted({source for source, _ in trechos}),
        candidatas=candidatas,
    )


@observe(name="run-agents", capture_input=False, capture_output=False)
async def run_agents(pergunta: str, session_id: str | None = None) -> RunAgentsResponse:
    logger.info("Requisição recebida pergunta=%r", pergunta)
    session_id = session_id or str(uuid.uuid4())
    langfuse = get_langfuse()
    # input/output do trace vêm do span raiz: só a pergunta e a resposta final
    langfuse.update_current_span(input=pergunta)

    with propagate_attributes(session_id=session_id, trace_name="run-agents", tags=["rag-api"]):
        resposta = await _run_pipeline(pergunta)

    resposta.session_id = session_id
    resposta.trace_id = langfuse.get_current_trace_id()
    langfuse.update_current_span(
        output=resposta.resposta or "(nenhuma resposta elegível)",
        metadata={"score": resposta.score, "fontes": resposta.fontes, "num_candidatas": len(resposta.candidatas)},
    )
    if resposta.score is not None:
        langfuse.score_current_trace(name="best-answer-score", value=resposta.score, data_type="NUMERIC")

    logger.info("Retornando resposta ao usuário session_id=%s trace_id=%s", session_id, resposta.trace_id)
    return resposta
