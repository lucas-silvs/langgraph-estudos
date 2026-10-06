import logging

# importado depois de config (load_dotenv) para o Langfuse ler as credenciais corretas
from . import config
from langfuse.openai import AsyncOpenAI  # noqa: E402

logger = logging.getLogger("rag.llm")

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Instancia o cliente OpenAI na primeira chamada e reutiliza nas seguintes."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)
        logger.info("Cliente OpenAI instanciado base_url=%s modelo=%s", config.LLM_BASE_URL, config.LLM_MODEL)
    return _client
