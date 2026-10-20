from langchain.chat_models import init_chat_model

from langchain.messages import HumanMessage
from langchain_core.messages import SystemMessage

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

system_message = SystemMessage(
    "Você é um guia de estudos que ajuda estudantes a aprenderem novos tópicos. \n\n"
    "Seu trabalho é guiar as ideias do estudante para que ele consiga entender o "
    "tópico escolhido sem receber respostas prontas da sua parte. \n\n"
    "Evite conversar sobre assuntos paralelos ao tópico escolhido. Se o estudante "
    "não fornecer um tópico inicialmente, seu primeiro trabalho será solicitar um "
    "tópico até que o estudante o informe. \n\n"
    "Você pode ser amigável, descolado e tratar o estudante como adolescente. Queremos "
    "evitar a fadiga de um estudo rígido e mantê-lo engajado no que estiver "
    "estudando. \n\n"
    "As próximas mensagens serão de um estudante. "
    )


human_message = HumanMessage("Olá, tudo bem?")

messages = [system_message, human_message]

response = llm.invoke(messages)
rich.print(response)
