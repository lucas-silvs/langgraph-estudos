import os
import sys
from pathlib import Path

os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app import agents  # noqa: E402
from app.main import app  # noqa: E402


def _patch(monkeypatch, respostas, scores):
    async def fake_search(pergunta, top_k):
        return [("doc.txt", "trecho")]

    async def fake_generate(pergunta, contexto, n):
        return respostas

    scores_by_answer = dict(zip(respostas, scores))

    async def fake_evaluate(pergunta, resposta, contexto):
        return scores_by_answer[resposta]

    monkeypatch.setattr(agents, "search", fake_search)
    monkeypatch.setattr(agents, "generate_answers", fake_generate)
    monkeypatch.setattr(agents, "evaluate_answer", fake_evaluate)


def test_retorna_melhor_resposta_elegivel(monkeypatch):
    _patch(monkeypatch, ["a", "b", "c"], [4.0, 8.5, 6.0])
    r = TestClient(app).post("/run/agents", json={"pergunta": "oi"})
    assert r.status_code == 200
    body = r.json()
    assert body["resposta"] == "b"
    assert body["score"] == 8.5
    assert [c["elegivel"] for c in body["candidatas"]] == [False, True, True]


def test_score_igual_ao_limiar_nao_e_elegivel(monkeypatch):
    _patch(monkeypatch, ["a", "b"], [5.0, 3.0])
    body = TestClient(app).post("/run/agents", json={"pergunta": "oi"}).json()
    assert body["resposta"] is None


def test_pergunta_vazia_retorna_422():
    r = TestClient(app).post("/run/agents", json={"pergunta": ""})
    assert r.status_code == 422


def test_parse_score():
    assert agents.parse_score("7,5") == 7.5
    assert agents.parse_score("Nota: 12") == 10.0
    assert agents.parse_score("sem número") == 0.0
