from typing import TypedDict
from rich import print
from langgraph.graph import StateGraph, add_messages
import operator
from typing import Annotated


# 1 - defini o meu estado
class State(TypedDict):
    nodes_path: Annotated[list[str], add_messages]


# 2 - defini os nodes


def node_a(state: State) -> None:

    print("> node a", f"{state=}")

    node_path = state["nodes_path"]

    outputState: State = {"nodes_path": [*node_path, "A"]}
    print("> node_a", f"{state=}", f"{outputState=}")
    return outputState
    pass


def node_b(state: State) -> None:
    print("> node b", f"{state=}")

    node_path = state["nodes_path"]

    outputState: State = {"nodes_path": [*node_path, "B"]}
    print("> node_b", f"{state=}", f"{outputState=}")

    # return {"nodes_path": node_path + ["B"]}
    return outputState


# Definir o builder do grafo

builder = StateGraph(State)

builder.add_node("A", node_a)
builder.add_node("B", node_b)

# conectar as edges (arestas)

builder.add_edge("__start__", "A")

builder.add_edge("A", "B")

builder.add_edge("B", "__end__")

# Compilar o grafico

graph = builder.compile()

graph.get_graph().draw_mermaid_png(output_file_path="graph.png")


response = graph.invoke({"nodes_path": []})

print()
print(f"{response=}")
print()
