from typing import Annotated, Sequence, TypedDict

from langgraph.graph import END, START, StateGraph, add_messages

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from langgraph.checkpoint.memory import InMemorySaver

from langgraph.graph.state import  RunnableConfig

from rich import print
from rich.markdown import Markdown

from langchain.chat_models import init_chat_model

# from langchain.agents import AgentState
llm = init_chat_model("openai:google:gemma-4-12b")


# 1 - Defino o meu State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# 2 - Defino o meu node

def call_llm(state: AgentState) -> None:
    llm_result = llm.invoke(state["messages"])

    # llm_result = AIMessage("ola amigo")
    return {"messages": [llm_result]}

# 3 - Crio o StateGraph

builder = StateGraph(AgentState, context_schema=None, input_schema=AgentState, output_schema=AgentState)

builder.add_node("call_llm", call_llm)

# 4 - adicionar node ao grafo

builder.add_edge(START, "call_llm")
builder.add_edge("call_llm", END)

# 5 - Compilar o grafo


checkpointer = InMemorySaver()
config = RunnableConfig(configurable={ "thread_id": "001"})

graph = builder.compile()


if __name__ == "__main__":

    current_messages: Sequence[BaseMessage] = []

    while True:
        user_input = input("Digite sua mensagem: ")

        if user_input.lower() in ("quit", "q"):
            print("Bye!")
            print(Markdown('---'))

            break
        human_message = HumanMessage(user_input)
        current_messages = [*current_messages, human_message]
        result = graph.invoke({"messages": current_messages}, config = config) 
        print(Markdown(str(result["messages"][-1].content)))
        print(Markdown('---'))
        
    # user_input = "Ola Mundo!"
    # human_message = HumanMessage(user_input)
    # result = graph.invoke({"messages": [human_message]})
    # print(result["messages"][-1].content)
    # print(Markdown('---'))


