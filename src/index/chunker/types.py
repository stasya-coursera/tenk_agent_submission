
 
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, Final, List, Optional, Tuple
from pydantic import BaseModel
from index.types import ItemInfo, ItemName
from index.parser.types import FilingType


class ChunkType(str, Enum):
    """
    """
    REGULAR = "REGULAR"          
    # do I need other types?
  

class ChunkMetadata(BaseModel):
    """
    """                     
    chunk_type: ChunkType                    
    item: Optional[ItemName] = None
    item_anchor: Optional[str] = None # anchor/href from TOC for the item (e.g. "i7")
    item_title: Optional[str] = None
    item_description: Optional[str] = None
    page_numbers: Optional[List[str]] = None
    page_range: Optional[Tuple[str, str]] = None
    table_references: Optional[List[str]] = None 
    image_references: Optional[List[str]] = None
    # for debugging purposes
    order: Optional[int] = None
    structural_nodes_order: Optional[List[Decimal]] = None # order of structural nodes in the chunk
    structural_node_ids: Optional[List[str]] = None # structural nodes that were combined to create this chunk
    # Filing metadata from structural nodes
    company: Optional[str] = None # string, e.g. "Apple Inc."
    ticker: Optional[str] = None # string, e.g. "AAPL"
    form: Optional[FilingType] = None # string, e.g. "10-K"
    period_of_report: Optional[str] = None # string, e.g. "2025-09-27" 
    year: Optional[int] = None # int, e.g. 2024
    filing_url: Optional[str] = None # string, e.g. "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm"

    
    def __init__(self, **data):
        super().__init__(**data)
        if self.structural_node_ids is None:
            # initialize as empty list ( Avoid mutable default values)
            self.structural_node_ids = []

class ItemStatistics(BaseModel):
    """Statistics for a specific item."""
    chunk_count: int
    total_words: int
    min_words: int
    max_words: int
    avg_words: float
    table_chunks: int = 0
    total_tables: int = 0
    image_chunks: int = 0
    total_images: int = 0

class ChunkStatistics(BaseModel):
    """Statistics about chunk creation organized by item."""
    total_chunks: int
    total_words: int
    overall_min_words: int
    overall_max_words: int
    overall_avg_words: float
    number_of_unique_items: int
    items: Dict[str, ItemStatistics] = field(default_factory=dict)

@dataclass
class Chunk:
    id: str
    content: str
    metadata: ChunkMetadata = field(default_factory=ChunkMetadata)

@dataclass
class ItemChunkingConfig():
    min_chunk_size_words: int
    max_chunk_size_words: int
    chunk_overlap_words: int


DEFAULT_ITEM_CHUNKING_CONFIG: ItemChunkingConfig = ItemChunkingConfig(
    min_chunk_size_words=100,
    max_chunk_size_words=500,
    chunk_overlap_words=50,
)

ITEMS_CHUNKING_CONFIGS: Final[Dict[ItemName, ItemInfo]] = {
    "Item 1": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 1A": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 1B": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 1C": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 2": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 3": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 4": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 5": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 6": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 7": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 7A": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 8": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 9": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 9A": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 9B": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 9C": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 10": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 11": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 12": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 13": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 14": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 15": DEFAULT_ITEM_CHUNKING_CONFIG,
    "Item 16": DEFAULT_ITEM_CHUNKING_CONFIG,
}
