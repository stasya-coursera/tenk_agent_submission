"""This module defines the react_tools for agent."""

import click
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode

from react_agent.state import ReactGraphAnnotation
from react_agent.tools import document_qa, search, get_agent_available_data

react_tools = [document_qa, search, get_agent_available_data]

_base_tools_node = ToolNode(react_tools)


async def react_tools_node(
    state: ReactGraphAnnotation, config: RunnableConfig
) -> dict:
    """Custom tools node that prints which tool is being called with its inputs."""
    from langchain_core.messages import ToolMessage
    
    # Find the last AIMessage with tool_calls
    tool_calls_info = []
    for message in reversed(state.messages):
        if isinstance(message, AIMessage) and message.tool_calls:
            # Print each tool being called
            for tool_call in message.tool_calls:
                # Handle both dict and object formats
                if isinstance(tool_call, dict):
                    tool_name = tool_call.get("name", "unknown")
                    tool_args = tool_call.get("args", {})
                    tool_id = tool_call.get("id", "unknown")
                else:
                    tool_name = getattr(tool_call, "name", "unknown")
                    tool_args = getattr(tool_call, "args", {})
                    tool_id = getattr(tool_call, "id", "unknown")
                
                # Format the arguments for display
                args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
                click.echo(f"🔧 Executing tool: {tool_name}({args_str})")
                
                # Store info for logging results
                if tool_name == "document_qa":
                    requested_k = tool_args.get("k", 5)
                    tool_calls_info.append((tool_id, tool_name, requested_k))
            break
    
    # Delegate to the actual ToolNode
    result = await _base_tools_node.ainvoke(state, config)
    
    # Log results count for document_qa tool
    if "messages" in result:
        for msg in result["messages"]:
            if isinstance(msg, ToolMessage) and tool_calls_info:
                for tool_id, tool_name, requested_k in tool_calls_info:
                    if msg.tool_call_id == tool_id and tool_name == "document_qa":
                        # Count results returned
                        if isinstance(msg.content, list):
                            result_count = len(msg.content)
                        elif msg.content is None:
                            result_count = 0
                        else:
                            # If content is a string, try to parse it
                            result_count = 1 if msg.content else 0
                        break
    
    return result
