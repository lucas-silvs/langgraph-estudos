import os
import sys
import uuid
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.logging_metrics import log_run_metrics  # noqa: E402

load_dotenv()

langfuse = get_client()
langfuse_handler = CallbackHandler()

llm = ChatOpenAI(
    base_url=os.getenv("LLM_BASE_URL"),
    api_key="lm-studio",  # LM Studio ignora a key mas o client exige um valor
    model=os.getenv("LLM_MODEL"),
)


class GraphState(TypedDict):
    pergunta: str
    resposta: str


def gerar_resposta(state: GraphState) -> GraphState:
    mensagem = llm.invoke(state["pergunta"])
    return {"resposta": mensagem.content}


def formatar_saida(state: GraphState) -> GraphState:
    return {"resposta": f"Resposta final: {state['resposta'].strip()}"}


builder = StateGraph(GraphState)
builder.add_node("gerar_resposta", gerar_resposta)
builder.add_node("formatar_saida", formatar_saida)
builder.add_edge(START, "gerar_resposta")
builder.add_edge("gerar_resposta", "formatar_saida")
builder.add_edge("formatar_saida", END)

grafo = builder.compile()


def main() -> None:
    session_id = str(uuid.uuid4())
    resultado = grafo.invoke(
        {"pergunta": "Explique em uma frase o que é LangGraph."},
        config={
            "callbacks": [langfuse_handler],
            "metadata": {"langfuse_session_id": session_id},
        },
    )
    print(resultado["resposta"])

    trace_id = langfuse_handler.last_trace_id
    langfuse.flush()
    log_path = os.path.join(os.path.dirname(__file__), "metrics.log.jsonl")
    metricas = log_run_metrics(session_id, trace_id, log_path)
    print(metricas)


if __name__ == "__main__":
    main()
