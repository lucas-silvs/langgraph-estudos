import logging
import os

from dotenv import load_dotenv

load_dotenv()

# uvicorn só configura os próprios loggers; sem isto os logs de app.* não aparecem
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "local-model")
LLM_API_KEY = os.getenv("LLM_API_KEY", "lm-studio")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
NUM_CANDIDATES = int(os.getenv("NUM_CANDIDATES", "3"))
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "5.0"))
TOP_K = int(os.getenv("TOP_K", "3"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rag:rag@localhost:5433/rag")
