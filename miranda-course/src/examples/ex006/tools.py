

from langchain.tools import BaseTool, tool


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

@tool
def add(a: float, b: float) -> float:
    """Add two numbers.
    
    Args:
        a: float addend.
        b: float addend.

    Returns:
        the resulting float of the equation a + b.
    """

    return a + b



@tool
def subtract(a: float, b: float) -> float:
    """Subtract two numbers.
    
    Args:
        a: float minuend.
        b: float subtrahend.

    Returns:
        the resulting float of the equation a - b.
    """

    return a - b

@tool
def divide(a: float, b: float) -> float:
    """Divide two numbers.
    
    Args:
        a: float dividend.
        b: float divisor.

    Returns:
        the resulting float of the equation a / b.
    """

    return a / b

TOOLS: list[BaseTool] = [multiply, add, subtract, divide]

TOOLS_BY_NAME : dict[str, BaseTool] = {tool.name: tool for tool in TOOLS}