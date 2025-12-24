#!/usr/bin/env python3
"""CLI interface for the RAG research agent."""

import asyncio
import os
import time
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig

# Load environment variables
load_dotenv()

@click.group()
def cli():
    """RAG Research Agent CLI"""
    pass


@cli.command()
def index():
    """Index documents into the vector database."""
    click.echo("🔄 Starting document indexing...")
    
    try:
        from index_graph.graph import graph as index_graph
        
        # Use default configuration (will use agent default configuration)
        config = RunnableConfig(configurable={})
        
        # Run the indexing
        result = asyncio.run(_run_index(index_graph, config))
        
        if "docs" in result and result["docs"] == []:
            click.echo("✅ Documents indexed successfully!")
        else:
            click.echo("❌ Indexing may have failed. Check the logs.")
            
    except Exception as e:
        click.echo(f"❌ Error during indexing: {e}")
        raise


@cli.command()
@click.argument("question", required=False)
def query(question: Optional[str]):
    """Query the indexed documents. If no question provided, enters interactive mode."""
    if question:
        # Single query mode
        click.echo(f"🔍 Searching for: {question}")
        try:
            answer = asyncio.run(_run_single_query(question))
            click.echo(f"\n💡 Answer: {answer}")
        except Exception as e:
            click.echo(f"❌ Error during query: {e}")
            raise
    else:
        # Interactive mode
        click.echo("🤖 Entering interactive mode. Type 'exit' or 'quit' to stop.")
        asyncio.run(_run_interactive_query())


async def _run_index(index_graph, config: RunnableConfig):
    """Run the indexing graph."""
    return await index_graph.ainvoke({"docs": None}, config=config)


async def _run_single_query(question: str, thread_id: str = None) -> str:
    """Run a single query and return the answer."""
    from react_agent.graph import react_graph
    
    # Use default configuration 
    if thread_id is None:
        thread_id = f"cli_query_{hash(question)}_{int(time.time() * 1000000)}"
        
    config = RunnableConfig(
        configurable={},
        thread_id=thread_id,
        recursion_limit=10
    )
    
    # Create the input state with fresh message history
    input_state = {
        "messages": [{"role": "user", "content": question}]
    }
    
    # Stream the execution to show progress and collect final state
    final_state = None
    async for chunk in react_graph.astream(input_state, config=config):
        for node_name, node_output in chunk.items():
            if node_name != "__end__" and node_name != "tools":
                # Skip printing "tools" node since we print specific tool names
                click.echo(f"🔧 Executing: {node_name}")
            # Keep updating with the latest state
            if node_output and isinstance(node_output, dict):
                final_state = node_output
    
    # Use the accumulated final state
    result = final_state if final_state else await react_graph.ainvoke(input_state, config=config)
    
    # Extract the final answer
    if "messages" in result and result["messages"]:
        last_message = result["messages"][-1]
        if hasattr(last_message, 'content'):
            return last_message.content
        elif isinstance(last_message, dict) and 'content' in last_message:
            return last_message['content']
        else:
            return str(last_message)
    
    return "No answer generated."


async def _run_interactive_query():
    """Run interactive query mode."""
    from react_agent.graph import react_graph
    
    click.echo("\n🤖 Welcome to interactive mode!")
    click.echo("Type your questions below. Type 'exit', 'quit', or 'q' to stop.\n")
    
    # Create a persistent thread for this interactive session
    session_thread_id = f"cli_interactive_{int(time.time() * 1000000)}"
    config = RunnableConfig(
        configurable={},
        thread_id=session_thread_id
    )
    
    # Initialize conversation state
    conversation_messages = []
    
    while True:
        try:
            # Get user input
            question = input("🗣️  Ask a question: ").strip()
            
            if question.lower() in ['exit', 'quit', 'q']:
                click.echo("\n👋 Goodbye!")
                break
                
            if not question:
                click.echo("Please enter a question.")
                continue
                
            # Show searching message
            click.echo(f"🔍 Searching for: {question}")
            
            # For the first question, use the same logic as single query mode
            if not conversation_messages:
                answer = await _run_single_query(question, session_thread_id)
                conversation_messages.append({"role": "user", "content": question})
                conversation_messages.append({"role": "assistant", "content": answer})
                click.echo(f"💡 Answer: {answer}\n")
                continue
            
            # For subsequent questions in the conversation
            conversation_messages.append({"role": "user", "content": question})
            
            # Create input state with full conversation history
            input_state = {"messages": conversation_messages}
            
            # Stream the execution to show progress and collect final state
            final_state = None
            async for chunk in react_graph.astream(input_state, config=config):
                for node_name, node_output in chunk.items():
                    if node_name != "__end__":
                        click.echo(f"🔧 Executing: {node_name}")
                    # Keep updating with the latest state
                    if node_output and isinstance(node_output, dict):
                        final_state = node_output
            
            # Use the accumulated final state
            result = final_state if final_state else {}
            
            # Extract and display the answer
            if "messages" in result and result["messages"]:
                # Update conversation with all messages from the result
                conversation_messages = result["messages"]
                last_message = result["messages"][-1]
                
                if hasattr(last_message, 'content'):
                    answer = last_message.content
                elif isinstance(last_message, dict) and 'content' in last_message:
                    answer = last_message['content']
                else:
                    answer = str(last_message)
                    
                click.echo(f"💡 Answer: {answer}\n")
            else:
                click.echo("💡 Answer: No answer generated.\n")
            
        except KeyboardInterrupt:
            click.echo("\n\n👋 Goodbye!")
            break
        except EOFError:
            click.echo("\n\n👋 Goodbye!")
            break
        except Exception as e:
            click.echo(f"❌ Error: {e}")
            click.echo("Please try again or type 'exit' to quit.\n")


if __name__ == "__main__":
    cli()
