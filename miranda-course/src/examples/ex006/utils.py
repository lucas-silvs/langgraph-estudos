from langchain.chat_models import BaseChatModel, init_chat_model


def load_llm() -> BaseChatModel:
    return init_chat_model("openai:openai:gpt-oss-20b")