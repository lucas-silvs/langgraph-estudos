import logging
import time

import psycopg
from langfuse import get_client as get_langfuse
from langfuse import observe
from pgvector import Vector
from pgvector.psycopg import register_vector_async

from . import config
from .llm import get_client

logger = logging.getLogger("rag.retrieval")


async def embed(texts: list[str]) -> list[list[float]]:
    response = await get_client().embeddings.create(
        name="embed-texts", model=config.EMBEDDING_MODEL, input=texts
    )
    return [item.embedding for item in response.data]


async def _connect() -> psycopg.AsyncConnection:
    conn = await psycopg.AsyncConnection.connect(config.DATABASE_URL)
    await register_vector_async(conn)
    return conn


async def add_documents(chunks: list[tuple[str, str]]) -> None:
    """Insere pares (source, content) já com o embedding calculado."""
    embeddings = await embed([content for _, content in chunks])
    async with await _connect() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(
                "INSERT INTO documents (source, content, embedding) VALUES (%s, %s, %s)",
                [(s, c, e) for (s, c), e in zip(chunks, embeddings)],
            )
        await conn.commit()


@observe(as_type="retriever", name="retrieve-context", capture_input=False, capture_output=False)
async def search(pergunta: str, top_k: int) -> list[tuple[str, str]]:
    """Retorna os top_k trechos (source, content) mais próximos por distância de cosseno."""
    get_langfuse().update_current_span(input=pergunta, metadata={"top_k": top_k, "index": "documents"})
    logger.info("Consultando base vetorial (pgvector) top_k=%d", top_k)
    start = time.perf_counter()
    [query_embedding] = await embed([pergunta])
    async with await _connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT source, content FROM documents ORDER BY embedding <=> %s LIMIT %s",
                (Vector(query_embedding), top_k),
            )
            rows = await cur.fetchall()
    logger.info(
        "Base vetorial retornou %d trechos fontes=%s em %.0f ms",
        len(rows),
        sorted({source for source, _ in rows}),
        (time.perf_counter() - start) * 1000,
    )
    get_langfuse().update_current_span(output=[{"source": s, "content": c} for s, c in rows])
    return rows
