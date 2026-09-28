import os
import sys
import uuid

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langfuse import get_client
from langfuse.langchain import CallbackHandler

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

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "Você é um assistente objetivo."),
        ("human", "{pergunta}"),
    ]
)

chain = prompt | llm | StrOutputParser()


def main() -> None:
    session_id = str(uuid.uuid4())
    resposta = chain.invoke(
        {"pergunta": "Explique em uma frase o que é LangChain."},
        config={
            "callbacks": [langfuse_handler],
            "metadata": {"langfuse_session_id": session_id},
        },
    )
    print(resposta)

    trace_id = langfuse_handler.last_trace_id
    langfuse.flush()
    log_path = os.path.join(os.path.dirname(__file__), "metrics.log.jsonl")
    metricas = log_run_metrics(session_id, trace_id, log_path)
    print(metricas)


if __name__ == "__main__":
    main()
