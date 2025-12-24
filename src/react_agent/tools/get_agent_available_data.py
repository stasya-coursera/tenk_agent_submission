"""Tool to get information about available data in the vector store."""

from typing import Annotated, Any, List, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool


@tool(parse_docstring=True)
async def get_agent_available_data() -> Optional[list[dict[str, Any]]]:
    """Get the filings that are available to the agent
    Use this tool when you need:
    - know which filings you have in the system and which require using external data.
    - 
    
    Returns:
        List[dict[str, Any]]: A list of available filings with company, form, year, and filing information.
    """
    return [
        {
            "form": "10-K", 
            "year": 2025, 
            "ticker": "AAPL", 
            "company": "Apple Inc.", 
            "filing_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm", 
            "filing_valid_until": "2025-09-27"
        }
    ]
