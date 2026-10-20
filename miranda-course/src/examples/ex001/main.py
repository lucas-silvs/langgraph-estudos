from langchain.chat_models import init_chat_model

import rich

"""
Example of initializing a chat model with LangChain using the OpenAI API.
llm = init_chat_model(
    "google/gemma-4-12b",
    model_provider="openai",
    base_url="http://127.0.0.1:1234/v1",
    api_key=openai_api_key or "lm-studio",
)

"""
llm = init_chat_model("openai:google:gemma-4-12b")

response = llm.invoke("olá, tudo bem?")
rich.print(response)
