

from langchain.messages import HumanMessage, SystemMessage
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from rich.markdown import Markdown
from rich.prompt import Prompt

from examples.ex006.graph import build_graph
from rich import print

from examples.ex006.prompt import SYSTEM_PROMPT


def main() -> None:
    config = RunnableConfig(configurable={"thread_id": 1})
    graph = build_graph()

    all_messages: list[BaseMessage] = []

    prompt = Prompt()

    Prompt.prompt_suffix = ""

    while True:
        user_input = prompt.ask("[bold cyan]Você: \n")
        print(Markdown("\n\n --- \n\n"))

        if user_input.lower() in ["q", "quit"]:
            break

        human_message = HumanMessage(user_input)
        current_loop_messages = [human_message]

        if len(all_messages) == 0:
            current_loop_messages = [SystemMessage(SYSTEM_PROMPT), human_message]

        result = graph.invoke({"messages": current_loop_messages}, config=config)

        print("[bold cyan]RESPOSTA: \n")
        print(Markdown(result["messages"][-1].content))
        print(Markdown("\n\n --- \n\n"))
if __name__ == "__main__":
    main()