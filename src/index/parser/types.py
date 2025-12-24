from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, List, Optional, Literal, Dict
from bs4 import Tag
import pandas as pd
import uuid
from io import StringIO
from pydantic import BaseModel
from ..types import ItemName
from .constants import (
    MAX_COLUMNS_TO_SHOW,
    MAX_NUMERIC_COLUMNS_TO_SHOW, 
    MAX_DATE_COLUMNS_TO_SHOW,
    COLUMN_OVERFLOW_THRESHOLD,
    EMPTY_TABLE_MESSAGE
)

@dataclass
class FilingType(str, Enum):
    TEN_K = "10-K"
    
StructuralNodeType = Literal[
    "text",
    "table",
    "image",
    "page_footer", # contains page number, discarded after enrichment
    "non_content", # decorative elements, hr, empty text, etc. - can be used to extract semantic meaning, discarded after enrichment
]
    
@dataclass
class StructuralNodeMetadata:
    parent_item: Optional[ItemName] = None
    item_anchor: Optional[str] = None # anchor/href from TOC for the item (e.g. "i7")
    page_number: Optional[int] = None # page number extracted from page footer element
    structural_order: Optional[int] = None 
    structural_node_id: Optional[str] = None # unique identifier for this structural node
    company: Optional[str] = None # string, e.g. "Apple Inc."
    ticker: Optional[str] = None # string, e.g. "AAPL"
    form: Optional[FilingType] = None # string, e.g. "10-K"
    filing_date: Optional[datetime] = None # datetime object
    period_of_report: Optional[str] = None # string, e.g. "2025-09-27" 
    year: Optional[int] = None # int, e.g. 2024
    filing_url: Optional[str] = None # string, e.g. "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm"
    

@dataclass
class StructuralNode:
    node_type: StructuralNodeType
    element: Tag   
    metadata: StructuralNodeMetadata
    


@dataclass
class TextNode(StructuralNode):
    # remove default text field input; initialize in __post_init__
    text: str = field(init=False)

    @classmethod
    def from_element(cls, element: Tag):
        """Create TextNode from element"""
        from .parser import extract_text
        text = extract_text(element)
        if text is None:
            raise ValueError(f"Element is not a text node: {element.name}")
        metadata = StructuralNodeMetadata()
        metadata.structural_node_id = f"text_{uuid.uuid4().hex[:12]}"
        return cls(
            node_type="text",
            element=element,
            metadata=metadata
        )

    def __post_init__(self):
        
        # always extract text from element
        self.text = self.element.get_text(separator=" ", strip=True)

class TableMetadata(BaseModel):
    """Structured metadata about the table contents – perfect for LLM context or embedding prompts."""
    table_id: str
    column_names: List[str]
    row_names: List[str]

class TableLookup(BaseModel):
    """Fast-lookup structure mapping (row_name, column_name) → cell value.
    Row names are unique (include row number in parentheses to handle duplicates)."""
    data: Dict[tuple[str, str], Any]

@dataclass
class TableNode(StructuralNode):
    dataframe: pd.DataFrame = field(init=False)
    caption: str = field(init=False)
    text: str = field(init=False)
    min_text: str = field(init=False) # the minimal representation of the table
    table_metadata: TableMetadata = field(init=False)
    table_lookup: TableLookup = field(init=False)
    

    @classmethod
    def from_element(cls, element: Tag):
        """Create TableNode from element"""
        from .parser import extract_table
        
        table = extract_table(element)
        if table is None:
            raise ValueError(f"Element is not a table node: {element.name}")
        metadata = StructuralNodeMetadata()
        metadata.structural_node_id = f"table_{uuid.uuid4().hex[:12]}"

        return cls(
            node_type="table",
            element=element,
            metadata=metadata
        )

    def __post_init__(self):
        
        table = self.element.find("table")
        
        # Extract caption
        if table:
            caption_elem = table.find("caption")
            self.caption = caption_elem.get_text(strip=True) if caption_elem else ""
        else:
            self.caption = ""

        # Parse the table into a DataFrame (exploded with unique column names)
        exploded_df = parse_html_table(table)
        
        # Merge consecutive columns with the same base name
        self.dataframe = merge_dataframe_columns(exploded_df)
        
        # Use merged DataFrame for embedding and retrieval
        self.table_metadata = TableForEmbedding(df = self.dataframe, table_id = self.metadata.structural_node_id)
        self.table_lookup = TableForRetrieval(df = self.dataframe, table_id = self.metadata.structural_node_id)
        # Generate text representation of the table
        self.text = TableForEmbedding(self.dataframe, self.metadata.structural_node_id).model_dump_json()
        self.text = self._generate_text()
        self.min_text = self._generate_min_text()
    
    def _generate_text(self) -> str:
        """Generate a text representation of the table."""
        parts = []
        
        # Add caption if present
        if self.caption:
            parts.append(f"Table Caption: {self.caption}")
        
        # create a string with all values of the lookup data
        for key, value in self.table_lookup.data.items():
            # Format key tuple as (row_name, column_name)
            row_name, col_name = key
            # Convert value to string, handling pandas Series or other types
            value_str = str(value).strip() if value is not None else ""
            # Replace any internal newlines in the value with spaces to keep formatting clean
            value_str = value_str.replace('\n', ' ').replace('\r', ' ')
            parts.append(f"({row_name}, {col_name}) -> {value_str}")
        
        return "\n".join(parts)
    
    def _generate_min_text(self) -> str:
        """Generate a meaningful markdown text representation of the table."""
        return self.table_metadata.model_dump_json()
    
def parse_html_table(table: Tag) -> pd.DataFrame:
    """
    Parse an HTML table into a pandas DataFrame.
    
    Strategy:
    1. Expand all colspan cells to create a properly aligned grid
    2. Identify header row(s)
    3. Extract column names from headers
    4. Extract row names from first column of data rows
    5. Create DataFrame with columns and index set correctly
    
    Args:
        table: BeautifulSoup Tag object of <table>
    
    Returns:
        pd.DataFrame with proper column names and row index
    """
    if not table:
        return pd.DataFrame()
    
    # Step 1: Get all rows
    rows = table.find_all("tr")
    if not rows:
        return pd.DataFrame()
    
    # Step 2: Helper function to check if a row is a header
    def is_header_row(row: Tag) -> bool:
        """Check if a row looks like a header."""
        if row.find("th"):
            return True
        # Check for bold text
        if row.find(["b", "strong"]):
            return True
        # Check for bold style in spans
        for span in row.find_all("span"):
            style = span.get("style", "")
            if style and ("font-weight:700" in str(style).lower() or "font-weight:bold" in str(style).lower()):
                return True
        return False
    
    # Step 3: Find header row index
    header_idx = None
    for i, row in enumerate(rows):
        if is_header_row(row):
            header_idx = i
            break
    
    # If no header found, use first row
    if header_idx is None:
        header_idx = 0
    
    # Step 4: Process header row to make duplicate names unique BEFORE exploding
    header_row_tag = rows[header_idx]
    header_cells = header_row_tag.find_all(["td", "th"])
    header_name_counts = {}  # Track how many times we've seen each header name
    header_name_total_counts = {}  # Track total count of each header name
    header_cell_info = []  # Store (base_name, duplicate_index, is_duplicate) for each header cell
    
    # First pass: count total occurrences of each header name
    for cell in header_cells:
        text = cell.get_text(strip=True).replace('\u00a0', ' ').strip()
        if text:
            header_name_total_counts[text] = header_name_total_counts.get(text, 0) + 1
    
    # Second pass: create unique names, only adding duplicate index if name appears multiple times
    # Also track consecutive empty cells to give them unique group indices
    empty_col_group_index = -1  # Track which empty column group we're in
    prev_was_empty = False  # Track if previous cell was empty
    
    for cell in header_cells:
        text = cell.get_text(strip=True).replace('\u00a0', ' ').strip()
        if text:
            is_duplicate = header_name_total_counts[text] > 1
            # Count occurrences to make unique (only for duplicates)
            if text not in header_name_counts:
                header_name_counts[text] = 0
            else:
                header_name_counts[text] += 1
            
            # Store base name, duplicate index, and whether it's a duplicate
            duplicate_index = header_name_counts[text] if is_duplicate else None
            header_cell_info.append((text, duplicate_index, is_duplicate))
            prev_was_empty = False
        else:
            # Empty cell - track consecutive groups
            if not prev_was_empty:
                # Start of a new empty column group
                empty_col_group_index += 1
            # Store as empty_col with group index
            header_cell_info.append(("empty_col", empty_col_group_index, True))  # Always treat as "duplicate" to get the group index
            prev_was_empty = True
    
    # Step 5: Expand colspan to create a 2D grid
    def expand_row(row: Tag, is_header: bool = False, header_cell_info: Optional[List[tuple]] = None) -> List[str]:
        """Expand a row, handling colspan.
        
        For headers: repeat unique name for each colspan (so we know which columns belong to which header)
        For data rows: put text only in first position, leave rest empty
        """
        expanded = []
        cell_index = 0
        
        for cell in row.find_all(["td", "th"]):
            colspan = int(cell.get("colspan", 1))
            text = cell.get_text(strip=True).replace('\u00a0', ' ').strip()
            
            if is_header and header_cell_info and cell_index < len(header_cell_info):
                # Use the header cell info we created earlier
                base_name, duplicate_index, is_duplicate = header_cell_info[cell_index]
                if base_name:
                    # For headers: create column names based on whether it's a duplicate
                    for i in range(colspan):
                        if is_duplicate:
                            # Duplicate or empty_col: base_name__duplicate_index__exploded_index
                            expanded.append(f"{base_name}__{duplicate_index}__{i}")
                        else:
                            # Non-duplicate: base_name__exploded_index
                            expanded.append(f"{base_name}__{i}")
                else:
                    # This shouldn't happen now, but keep as fallback
                    for i in range(colspan):
                        expanded.append(f"Column__{len(expanded)}")
                cell_index += 1
            elif is_header:
                # Fallback: repeat text for each colspan
                if text:
                    for i in range(colspan):
                        expanded.append(f"{text}__{i}")
                else:
                    for i in range(colspan):
                        expanded.append(f"Column__{len(expanded)}")
                cell_index += 1
            else:
                # For data rows: put text in first position only, rest empty
                expanded.append(text)
                expanded.extend([''] * (colspan - 1))
        return expanded
    
    # Build grid with all rows expanded
    grid = []
    for i, row in enumerate(rows):
        # Check if this is a header row
        is_header = is_header_row(row)
        if i == header_idx:
            # Pass header cell info for header row
            expanded_row = expand_row(row, is_header=is_header, header_cell_info=header_cell_info)
        else:
            expanded_row = expand_row(row, is_header=is_header)
        if expanded_row:  # Only add non-empty rows
            grid.append(expanded_row)
    
    if not grid:
        return pd.DataFrame()
    
    # Step 6: Extract column names from header row (already unique and exploded)
    if header_idx < len(grid):
        header_row = grid[header_idx]
        final_column_names = header_row  # Already has unique exploded names
    else:
        return pd.DataFrame()
    
    # Step 6: Extract data rows (skip header row and empty rows)
    # We need to track the original row structure to get the colspan of the first cell
    data_rows = []
    row_names = []
    
    for i, row_tag in enumerate(rows):
        if i == header_idx:
            continue  # Skip header row
        
        # Get the original row structure to find first cell's colspan
        cells = row_tag.find_all(["td", "th"])
        if not cells:
            continue
        
        # Get the expanded row from grid
        if i < len(grid):
            row_data = grid[i]
        else:
            continue
        
        if not row_data or all(not cell.strip() for cell in row_data):
            continue  # Skip empty rows
        
        # First cell is the row name - get its colspan
        first_cell = cells[0]
        row_name_colspan = int(first_cell.get("colspan", 1))
        base_row_name = row_data[0].strip() if row_data[0].strip() else f"Row_{i}"
        # Append actual row number (position in table) to make row names unique (handles duplicates)
        row_name = f"{base_row_name} ({i})"
        row_names.append(row_name)
        
        # Create data row: set row name columns to empty (row name is stored in index)
        data = list(row_data)  # Copy the row data
        # Set the row name columns (0 to row_name_colspan-1) to empty strings
        for j in range(min(row_name_colspan, len(data))):
            data[j] = ''
        data_rows.append(data)
    
    if not data_rows:
        return pd.DataFrame()
    
    # Step 7: Normalize data row lengths to match header row length exactly
    num_cols = len(final_column_names)
    normalized_data = []
    for row in data_rows:
        if len(row) < num_cols:
            # Pad with empty strings
            normalized_row = row + [''] * (num_cols - len(row))
        elif len(row) > num_cols:
            # Truncate to match header length
            normalized_row = row[:num_cols]
        else:
            normalized_row = row
        normalized_data.append(normalized_row)
    
    # Step 7: Create DataFrame with proper columns and index
    df = pd.DataFrame(normalized_data, columns=final_column_names)
    
    # Set row names as index
    if row_names and len(row_names) == len(df):
        df.index = row_names
    
    return df

def merge_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge consecutive columns with the same merge key.
    
    Column naming patterns:
    - base_name__exploded_index (e.g., '2025__0', '2025__1', '2025__2') → merge to '2025'
    - base_name__group_index__exploded_index (e.g., 'Change__0__0', 'Change__0__1') → merge to 'Change__0'
    - empty_col__group_index__exploded_index (e.g., 'empty_col__0__0', 'empty_col__0__1') → merge to 'empty_col__0'
    
    Only merges consecutive columns (no other columns in between).
    
    Args:
        df: DataFrame with exploded columns
    
    Returns:
        New DataFrame with merged columns
    """
    import re
    
    def get_merge_key(col_name: str) -> str:
        """
        Extract the merge key from a column name.
        Examples:
        - '2025__0' → '2025'
        - '2025__1' → '2025'
        - 'Change__0__0' → 'Change__0'
        - 'Change__0__1' → 'Change__0'
        - 'empty_col__0__0' → 'empty_col__0'
        """
        col_str = str(col_name)
        # Pattern: base_name__group_index__exploded_index or base_name__exploded_index
        # We want everything except the last __number
        parts = col_str.split('__')
        if len(parts) >= 3:
            # Has group index: base_name__group_index__exploded_index
            # Return base_name__group_index
            return '__'.join(parts[:-1])
        elif len(parts) == 2:
            # No group index: base_name__exploded_index
            # Return base_name
            return parts[0]
        else:
            # No separators, return as is
            return col_str
    
    def merge_values(values: List[str]) -> str:
        """Combine multiple cell values into a single merged value."""
        # Filter out empty strings and combine non-empty values
        non_empty = [str(v).strip() for v in values if str(v).strip()]
        if not non_empty:
            return ''
        # Join with no separator (e.g., '$' + '34,550' → '$34,550')
        return ''.join(non_empty)
    
    # Find consecutive groups of columns with the same merge key
    column_list = list(df.columns)
    column_groups: List[tuple[str, List[str]]] = []  # List of (merge_key, [col_names])
    
    i = 0
    while i < len(column_list):
        col = column_list[i]
        merge_key = get_merge_key(col)
        
        # Collect consecutive columns with the same merge key
        group_cols = [col]
        j = i + 1
        while j < len(column_list):
            next_col = column_list[j]
            next_merge_key = get_merge_key(next_col)
            if next_merge_key == merge_key:
                group_cols.append(next_col)
                j += 1
            else:
                break
        
        # If we have multiple consecutive columns, merge them
        if len(group_cols) > 1:
            column_groups.append((merge_key, group_cols))
            i = j
        else:
            # Single column, keep as is
            column_groups.append((str(col), [col]))
            i += 1
    
    # Create merged DataFrame
    merged_data = {}
    column_order = []
    
    for merge_key, cols in column_groups:
        if len(cols) == 1:
            # Single column, no merging needed
            merged_data[merge_key] = df[cols[0]]
        else:
            # Multiple consecutive columns, merge them
            merged_values = []
            for idx in df.index:
                row_values = [df.at[idx, col] for col in cols]
                merged_value = merge_values(row_values)
                merged_values.append(merged_value)
            merged_data[merge_key] = merged_values
        
        column_order.append(merge_key)
    
    # Create new DataFrame with merged columns in original order
    merged_df = pd.DataFrame(merged_data, index=df.index)
    merged_df = merged_df[column_order]
    
    return merged_df

def TableForRetrieval(df: pd.DataFrame, table_id: str) -> TableLookup:
    """
    Creates a structured lookup object with a dictionary:
    (row_name, column_name) → cell_value
    Uses the merged column names from the DataFrame (e.g., '2025', 'Change__0', 'empty_col__0').
    Row names are unique (include row number in parentheses to handle duplicates).
    """
    metadata = TableForEmbedding(df = df, table_id = table_id)

    lookup_dict: Dict[tuple[str, str], Any] = {}
    for row_idx, row_name in zip(df.index, metadata.row_names):
        # Use the merged column names from DataFrame
        for col_name in df.columns:
            # Skip empty_col columns
            if str(col_name).startswith('empty_col'):
                continue
            
            cell_value = df.at[row_idx, col_name]
            
            # Skip empty values
            if not cell_value or (isinstance(cell_value, str) and not cell_value.strip()):
                continue
            
            # Row names are now unique (include row number), so we don't need row index in key
            lookup_key = (row_name, str(col_name))
            lookup_dict[lookup_key] = cell_value
    
    return TableLookup(data=lookup_dict)


def TableForEmbedding(df: pd.DataFrame, table_id: str) -> TableMetadata:
    """
    Returns structured metadata with flattened string lists of column and row names.
    Ideal for sending to an LLM so it knows what data exists in the table.
    Uses the merged column names from the DataFrame (e.g., '2025', 'Change__0').
    Filters out empty_col columns.
    """
    # Use the merged column names from DataFrame, filtering out empty_col columns
    if isinstance(df.columns, pd.MultiIndex):
        column_names = [' | '.join(map(str, col)).strip() for col in df.columns if not str(col).startswith('empty_col')]
    else:
        column_names = [str(col) for col in df.columns if not str(col).startswith('empty_col')]
    
    # Flatten row names (index)
    if isinstance(df.index, pd.MultiIndex):
        row_names = [' | '.join(map(str, row)).strip() for row in df.index]
    else:
        row_names = df.index.astype(str).tolist()
    
    return TableMetadata(table_id=table_id, column_names=column_names, row_names=row_names)


@dataclass
class ImageNode(StructuralNode):
    img_src: str = ""
    img_alt: str = ""
    text: str = field(init=False)
    min_text: str = field(init=False)

    @classmethod
    def from_element(cls, element: Tag):
        """Create ImageNode from element"""
        from .parser import extract_image
        img = extract_image(element)
        
        if img is None:
            raise ValueError(f"Element is not an image node: {element.name}")
        
        metadata = StructuralNodeMetadata()
        metadata.structural_node_id = f"image_{uuid.uuid4().hex[:12]}"
        return cls(
            node_type="image",
            element=element,
            metadata=metadata,
            img_src=img.get("src", ""),
            img_alt=img.get("alt", "")
        )
    
    def __post_init__(self):
        """Generate text representation of the image."""
        parts = []
        
        if self.img_alt:
            parts.append(f"Image description: {self.img_alt}")
        
        if self.img_src:
            parts.append(f"Image source: {self.img_src}")
        
        # Add reference to fetch complete image data if node has an ID
        if self.metadata.structural_node_id:
            parts.append(f"For complete image content, fetch image ID: {self.metadata.structural_node_id}")
        
        self.text = "[" + " ".join(parts) if parts else "Image content" + "]"
        self.min_text = "[" + " ".join(parts) if parts else "Image content" + "]"
        
@dataclass
class PageFooterNode(StructuralNode):
    page_number: int = 0
    @classmethod
    def from_element(cls, element: Tag):
        """Create PageFooterNode from element"""
        from .parser import extract_page_footer
        page_number = extract_page_footer(element)
        if page_number is None:
            raise ValueError(f"Element is not a page footer node: {element.name}")
        metadata = StructuralNodeMetadata()
        metadata.structural_node_id = f"footer_{uuid.uuid4().hex[:12]}"
        return cls(
            node_type="page_footer",
            element=element,
            metadata=metadata,
            page_number=page_number
        )
        
@dataclass
class NonContentNode(StructuralNode):
    reason: str = ""
    
    @classmethod
    def from_element(cls, element: Tag):
        """Create NonContentNode from element"""
        from .parser import is_non_content
        if not is_non_content(element):
            raise ValueError(f"Element is not a non-content node: {element.name}")
        
        reason = ""
        if element.find("hr"):
            reason = "contains_hr"
        elif not element.get_text(strip=True):
            reason = "empty_text"
        else:
            reason = "decorative"
        
        metadata = StructuralNodeMetadata()
        metadata.structural_node_id = f"noncontent_{uuid.uuid4().hex[:12]}"
        return cls(
            node_type="non_content",
            element=element,
            metadata=metadata,
            reason=reason
        )

"""
Helper class to iterate over a list of StructuralNodes and group them by item
"""
class ItemView:
    def __init__(self, item: ItemName, nodes: List[StructuralNode]):
        self.item = item
        self.nodes = nodes

    def __iter__(self) -> Iterable[StructuralNode]:
        """Allows: for node in item"""
        yield from self.nodes

    # Page-aware helpers
    def page_numbers(self) -> List[int]:
        return sorted({
            node.metadata.page_number
            for node in self.nodes
            if node.metadata.page_number is not None
        })

    def page_range(self) -> Optional[tuple[int, int]]:
        pages = self.page_numbers()
        if not pages:
            return None
        return pages[0], pages[-1]

"""
Helper class to iterate over a list of StructuralNodes and group them by item
"""
class SemanticDocument:
    def __init__(self, nodes: List[StructuralNode]):
        self._nodes = nodes

    def __iter__(self) -> Iterable[ItemView]:
        """Primary iteration: by item"""
        current_item: Optional[ItemName] = None
        bucket: List[StructuralNode] = []

        for node in self._nodes:
            item = node.metadata.parent_item
            if item != current_item:
                if current_item is not None:
                    yield ItemView(current_item, bucket)
                current_item = item
                bucket = []
            bucket.append(node)

        if current_item is not None:
            yield ItemView(current_item, bucket)

    def get_item(self, item_name: ItemName) -> Optional[ItemView]:
        """Return the ItemView for a specific item, or None if not present"""
        for item in self:
            if item.item == item_name:
                return item
        return None


class ItemParsingStatistics(BaseModel):
    """Statistics for parsing a specific item."""
    node_count: int
    text_nodes: int = 0
    table_nodes: int = 0
    image_nodes: int = 0
    page_footer_nodes: int = 0
    non_content_nodes: int = 0
    total_text_length: int = 0
    avg_text_length: float = 0.0


class ParsingStatistics(BaseModel):
    """Statistics about structural node creation organized by item."""
    total_nodes: int
    total_text_nodes: int
    total_table_nodes: int
    total_image_nodes: int
    total_page_footer_nodes: int
    total_non_content_nodes: int
    nodes_after_cleaning: int
    number_of_unique_items: int
    items: Dict[str, ItemParsingStatistics] = field(default_factory=dict)
