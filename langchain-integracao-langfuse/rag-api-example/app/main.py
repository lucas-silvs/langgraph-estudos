from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from langfuse import get_client as get_langfuse
from openai import APIConnectionError, APIStatusError
from psycopg import OperationalError

from .agents import run_agents
from .schemas import RunAgentsRequest, RunAgentsResponse


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    get_langfuse().shutdown()  # envia os eventos pendentes antes de encerrar


app = FastAPI(title="RAG API", lifespan=lifespan)


@app.post("/run/agents", response_model=RunAgentsResponse)
async def run_agents_endpoint(body: RunAgentsRequest) -> RunAgentsResponse:
    try:
        return await run_agents(body.pergunta, body.session_id)
    except (APIConnectionError, APIStatusError) as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao acionar o servidor LLM: {exc}") from exc
    except OperationalError as exc:
        raise HTTPException(status_code=503, detail=f"Banco vetorial indisponível: {exc}") from exc
