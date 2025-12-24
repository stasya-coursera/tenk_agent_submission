"""It includes a basic Tavily search function."""

from typing import Annotated, Any, Optional, cast

from dotenv import find_dotenv, load_dotenv
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from react_agent.configuration import Configuration

_: bool = load_dotenv(find_dotenv())

import warnings
warnings.filterwarnings(
    "ignore",
    message="Field name .* shadows an attribute in parent",
)

from langchain_tavily import TavilySearch


@tool(parse_docstring=True)
async def search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> Optional[list[dict[str, Any]]]:
    """Search for general web results.

    Args:
      query: The query to search for.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for finding information on a wide range of topics.
    """
    configuration = Configuration.from_runnable_config(config)
    wrapped = TavilySearch(max_results=configuration.max_search_results)
    result = await wrapped.ainvoke({"query": query})
    return cast(list[dict[str, Any]], result)
