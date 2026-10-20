from dataclasses import dataclass
from typing import Annotated, Literal

from langgraph.graph import END, START, StateGraph, add_messages
from rich import print


@dataclass
# 1 - defini o meu estado
class State:
    nodes_path: Annotated[list[str], add_messages]
    current_number: int = 0


# 2 - defini os nodes


def node_a(state: State) -> None:

    print("> node a", f"{state=}")

    node_path = state.nodes_path

    outputState: State = State(
        nodes_path=[*node_path, "A"], current_number=state.current_number
    )
    print("> node_a", f"{state=}", f"{outputState=}")
    return outputState


def node_b(state: State) -> None:
    print("> node b", f"{state=}")

    node_path = state.nodes_path

    outputState: State = State(
        nodes_path=[*node_path, "B"], current_number=state.current_number
    )
    print("> node_b", f"{state=}", f"{outputState=}")

    # return {"nodes_path": node_path + ["B"]}
    return outputState


def node_c(state: State) -> None:
    print("> node c", f"{state=}")

    node_path = state.nodes_path

    outputState: State = State(nodes_path=[*node_path, "C"])
    print("> node_c", f"{state=}", f"{outputState=}")

    # return {"nodes_path": node_path + ["C"]}
    return outputState


# Definir o builder do grafo

builder = StateGraph(State)

builder.add_node("A", node_a)
builder.add_node("B", node_b)
builder.add_node("C", node_c)

# Função condicional


def the_conditional(state: State) -> Literal["aresta_B", "aresta_C"]:

    if state.current_number >= 50:
        return "aresta_C"
    return "aresta_B"


# conectar as edges (arestas)

builder.add_edge(START, "A")

builder.add_conditional_edges("A", the_conditional, {
    "aresta_B": "B",
    "aresta_C": "C"
})

builder.add_edge("B", END)
builder.add_edge("C", END)

# builder.add_edge("A", "B")

# builder.add_edge("B", END)

# Compilar o grafico

graph = builder.compile()

graph.get_graph().draw_mermaid_png(output_file_path="graph.png")


response = graph.invoke(State(nodes_path=[]))

print()
print(30*"-")
print(f"{response=}")
print()


response = graph.invoke(State(nodes_path=[], current_number=60))

print(30*"-")
print(f"{response=}")
print(30*"-")


graph.get_graph().draw_mermaid_png(output_file_path="graph2.png")