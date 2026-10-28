# criando uma tool
from typing import Literal

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from rich import print

from examples.ex006.state import State
from examples.ex006.tools import TOOLS_BY_NAME, TOOLS
from examples.ex006.utils import load_llm


def call_llm(state: State) -> State:
    print("passando pelo call_llm")
    llm_with_tools = load_llm().bind_tools(TOOLS)
    result = llm_with_tools.invoke(state["messages"])
    return {"messages": [result]}


def tool_node(state: State) -> State:
    print("passando pelo tool_node")

    llm_response = state["messages"][-1]
    if not isinstance(llm_response, AIMessage) or not getattr(
        llm_response, "tool_calls", None
    ):
        return state

    call = llm_response.tool_calls[0]
    name, args, id_ = call["name"], call["args"], call["id"]

    try:
        content = TOOLS_BY_NAME[name].invoke(args)

        print(f"Tool {name} invoked successfully with args: {args}")
        status = "success"
    except Exception as e:
        content = f"pleas fix the following error in tool: {name}: {e}"
        status = "error"

    tool_message = ToolMessage(content=content, tool_call_id=id_, status=status)

    return {"messages": [tool_message]}


def router(state: State) -> Literal["tools_node", "__end__"]:
    print("passando pelo router")

    llm_response = state["messages"][-1]

    if getattr(llm_response, "tool_calls", None):
        return "tools_node"
    return "__end__"


def build_graph() -> CompiledStateGraph[State, None, State, State]:
    builder = StateGraph(State)

    builder.add_node("call_llm", call_llm)
    builder.add_node("tools_node", tool_node)

    builder.add_edge(START, "call_llm")
    builder.add_conditional_edges("call_llm", router, ["tools_node", "__end__"])
    builder.add_edge("tools_node", "call_llm")
    builder.add_edge("call_llm", END)

    return builder.compile(checkpointer=InMemorySaver())
