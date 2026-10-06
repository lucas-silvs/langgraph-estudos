"""Carrega data/*.txt no pgvector (um chunk por parágrafo). Recria a tabela de dados a cada execução."""
import asyncio
from pathlib import Path

import psycopg

from app import config
from app.retrieval import add_documents

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_chunks() -> list[tuple[str, str]]:
    chunks = []
    for path in sorted(DATA_DIR.glob("*.txt")):
        for paragraph in path.read_text(encoding="utf-8").split("\n\n"):
            if paragraph.strip():
                chunks.append((path.name, paragraph.strip()))
    return chunks


async def main() -> None:
    chunks = load_chunks()
    with psycopg.connect(config.DATABASE_URL) as conn:
        conn.execute("TRUNCATE documents RESTART IDENTITY")
    await add_documents(chunks)
    print(f"{len(chunks)} trechos ingeridos de {DATA_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
