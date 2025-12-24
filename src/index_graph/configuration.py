"""Define the configurable parameters for the index graph."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from pydantic import BaseModel
from shared.configuration import BaseConfiguration


class SecFiling(BaseModel):
    """Represents a single SEC filing to process."""
    ticker: str
    year: int


@dataclass(kw_only=True)
class IndexConfiguration(BaseConfiguration):   
    
    sec_filings: List[SecFiling] = field(
        default_factory=lambda: [SecFiling(ticker="AAPL", year=2025)],
        metadata={
            "description": "List of SEC filings to process, each with ticker and year."
        },
    )
    
