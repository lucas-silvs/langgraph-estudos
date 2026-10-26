# criando uma tool
from langchain.tools import tool, BaseTool

from rich import print

from langchain.chat_models import init_chat_model

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers.
    
    Args:
        a: float multiplicand.
        b: float multiplier.

    Returns:
        the resulting float of the equation a * b.
    """

    return a * b


# result = multiply.invoke({"a": 3, "b": 4})
# print(f"Result: {result}")

llm = init_chat_model("openai:openai:gpt-oss-20b")

messages: list[BaseMessage] = []

system_message = SystemMessage(
    'You are a helpful assistant. You have acess to tools. whe the user ask' \
    'for something, first look if you have a tool that can solve that problem, format the tool response correctly before replying to the user.' \
    'When you use the tool multiply, formate the response like "The result of a * b is <result>".'
)

human_message = HumanMessage(
    'olá, meu nome é Lucas, quanto é 3 multiplicado por 4?'
)
messages.append(system_message)
messages.append(human_message)


tools: list[BaseTool] = [multiply]

tools_by_name = {tool.name: tool for tool in tools}

llm_with_tools = llm.bind_tools(tools)


llm_response = llm_with_tools.invoke(messages)
messages.append(llm_response)
# print(f"LLM Result: {llm_response}")


if isinstance(llm_response, AIMessage) and getattr(llm_response, "tool_calls", None):

    call = llm_response.tool_calls[0]
    name, args, id_ = call['name'], call['args'], call['id']


    try:
        content = tools_by_name[name].invoke(args)
        status= "success"
    except Exception as e:
        content = f"pleas fix the following error in tool: {name}: {e}"
        status = "error"

    tool_message = ToolMessage(content=content, tool_call_id=id_, status=status)


    messages.append(tool_message)

    llm_response = llm_with_tools.invoke(messages)

    messages.append(llm_response)

print (f"Tool Result: {messages}")

