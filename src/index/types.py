
from dataclasses import dataclass
from enum import Enum
from bs4 import Tag
from typing import Dict, Final, Literal, Optional
from dataclasses import dataclass
from typing import Optional, Dict

# • Business Overview: Description of operations, products, and strategy 
# • Risk Factors: Detailed risks that could impact the business (typically 20-40 pag
# • Management Discussion & Analysis (MD&A): Management's perspective on financial results 
# • Financial Statements: Balance sheets, income statements, cash flow statements 
# • Notes to Financial Statements: Detailed breakdowns and accounting policies 
# • Geographic/Segment Data: Revenue and performance by region and product line 

ItemName = Literal[
    "Item 1",
    "Item 1A",
    "Item 1B",
    "Item 1C",
    "Item 2",
    "Item 3",
    "Item 4",
    "Item 5",
    "Item 6",
    "Item 7",
    "Item 7A",
    "Item 8",
    "Item 9",
    "Item 9A",
    "Item 9B",
    "Item 9C",
    "Item 10",
    "Item 11",
    "Item 12",
    "Item 13",
    "Item 15",
    "Item 16",
]

@dataclass
class ItemInfo:
    item: ItemName         # "Item 7"
    technical_name: str    # internal identifier
    display_name: str      # human-readable
    description: str       # business meaning
    #description_for_developers: Optional[str] = None # description of the data in the item, like how large the item is , does it usually conatin tables etc. for documentation purposes
    
@dataclass
class ItemTOCElement(ItemInfo):
    anchor: str            # "i7"
    link_text: str         # the text of the link
    start_el: Optional[Tag] = None  # the first element of the item
    end_el: Optional[Tag] = None    # the last element of the item



