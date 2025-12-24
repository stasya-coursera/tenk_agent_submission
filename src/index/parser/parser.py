
import json
from typing import List, Optional

from index.types import ItemTOCElement
from index.constants import ITEMS
from .types import ImageNode, NonContentNode, PageFooterNode, SemanticDocument, StructuralNode, StructuralNodeType, TextNode, TableNode, ParsingStatistics, ItemParsingStatistics
import re

from typing import List
from bs4 import BeautifulSoup, Tag
from edgar import Company
from shared.logger import get_logger
import edgar

edgar.set_identity("SEC Semantic Chunker v1.0 research@example.com")
logger = get_logger(__name__)


class TenKParser:
    def __init__(
        self,
        html_file: str,
        structured_obj,
        ticker: str, 
        year: int
    ):
        self.html_file = html_file
        self.soup = BeautifulSoup(html_file, "html.parser")
        self.structured_obj = structured_obj

        # metadata
        # availiable fields:
        #         .company
        # .form - string, e.g. "10-K"
        # .period_of_report - string date, e.g. "2024-12-31"
        # .ticker 'AAPL'
        # .year - int, e.g. 2024
        # .filing_date (datetime object
              
        self.company = structured_obj.company
        self.form = structured_obj.form
        self.period_of_report = structured_obj.period_of_report # '2025-09-27'
        self.filing_date = structured_obj.filing_date
        self.ticker = ticker
        self.year = year
        self.filing_url = structured_obj._filing.filing_url # https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm
                
        # for item in structured_obj.items:
        #     full_text = structured_obj[item] # AttributeError("'TenK' object has no attribute 'get_section_text'")
            

        # # flat small chunks, including table elements
        # chunks = structured_obj.chunked_document.chunks
        # print chunks 20 to 30
            # for chunk in chunks[20:30]:
            #     print(chunk)
            #     print("--------------------------------")

    @classmethod
    def from_ticker_year(cls, ticker: str, year: int) -> "TenKParser":
        logger.debug(f"Retrieving 10-K filing for {ticker} in {year}")
        company = Company(ticker)
        filings = company.get_filings(form="10-K")

        try:
            filing = next(
                f for f in filings
                if f.filing_date.year == year
            )
        except StopIteration:
            raise ValueError(f"No 10-K filing found for {ticker} in {year}")
        logger.debug(f"Successfully retrieved 10-K filing for {ticker} in {year}")
        html = filing.html()
        structured_obj = filing.obj()

        return cls(
            html_file=html,
            structured_obj=structured_obj,
            ticker=ticker,
            year=year
        )
    
    def get_semantic_document(self, nodes: List[StructuralNode]) -> SemanticDocument:
        """
        Returns a SemanticDocument from the 10-k filing
        """
        # nodes = self._get_structured_nodes_clean()
        return SemanticDocument(nodes)
        
    def get_statistics(self, nodes: List[StructuralNode]) -> ParsingStatistics:
        """Get detailed statistics about the given structural nodes."""
        # Use the provided nodes
        all_nodes = nodes
        
        # Get cleaned nodes (after removing page_footer and non_content)
        cleaned_nodes = [node for node in all_nodes if node.node_type not in ["page_footer", "non_content"]]
        
        from collections import defaultdict
        
        # Count nodes by type globally
        total_counts = defaultdict(int)
        for node in all_nodes:
            total_counts[node.node_type] += 1
            
        # Group statistics by item
        item_stats = defaultdict(lambda: {
            'node_count': 0,
            'text_nodes': 0,
            'table_nodes': 0,
            'image_nodes': 0,
            'page_footer_nodes': 0,
            'non_content_nodes': 0,
            'total_text_length': 0,
            'text_lengths': []
        })
        
        for node in all_nodes:
            if node.metadata.parent_item:
                item = node.metadata.parent_item
                item_stats[item]['node_count'] += 1
                item_stats[item][f'{node.node_type}_nodes'] += 1
                
                # Calculate text length for text nodes
                if node.node_type == 'text' and hasattr(node, 'text'):
                    text_len = len(node.text) if node.text else 0
                    item_stats[item]['total_text_length'] += text_len
                    item_stats[item]['text_lengths'].append(text_len)
        
        # Build structured result
        items = {}
        for item, stats in item_stats.items():
            avg_text_length = (stats['total_text_length'] / len(stats['text_lengths']) 
                             if stats['text_lengths'] else 0.0)
            
            items[item] = ItemParsingStatistics(
                node_count=stats['node_count'],
                text_nodes=stats['text_nodes'],
                table_nodes=stats['table_nodes'],
                image_nodes=stats['image_nodes'],
                page_footer_nodes=stats['page_footer_nodes'],
                non_content_nodes=stats['non_content_nodes'],
                total_text_length=stats['total_text_length'],
                avg_text_length=avg_text_length
            )
        
        return ParsingStatistics(
            total_nodes=len(all_nodes),
            total_text_nodes=total_counts['text'],
            total_table_nodes=total_counts['table'],
            total_image_nodes=total_counts['image'],
            total_page_footer_nodes=total_counts['page_footer'],
            total_non_content_nodes=total_counts['non_content'],
            nodes_after_cleaning=len(cleaned_nodes),
            number_of_unique_items=len(items),
            items=items
        )
    
    def get_structured_nodes_stream(self) -> List[StructuralNode]:
        """
        Returns a list of StructuralNodes from the 10-k filing
        """
        logger.debug(f"Parcing structured nodes for {self.ticker} in {self.year}")
        
        nodes = self._get_structured_nodes()
        self._update_nodes_base_metadata(nodes)
        self._update_nodes_metadata_page_number(nodes)
        
        #remove page_footer nodes
        nodes = [node for node in nodes if node.node_type != "page_footer"]
        
        # remove non content nodes
        nodes = [node for node in nodes if node.node_type != "non_content"]
        
        # assign structural_order after filtering to ensure no gaps
        for i, node in enumerate(nodes):
            node.metadata.structural_order = i
            
        logger.info(f"Successfully parsed {len(nodes)} structured nodes for {self.ticker} in {self.year}")
                # Always calculate statistics and let logger decide whether to show debug output
        statistics = self.get_statistics(nodes)
        logger.debug(f"Parsing statistics: {json.dumps(statistics.model_dump(), indent=2)}")
        return nodes
    
    def _get_structured_nodes(self) -> List[StructuralNode]:
        """
        Returns a list of StructuralNodes from the 10-k filing
        """
        # get the toc items
        toc_items = self._get_toc_items()
        # create the nodes
        nodes = []
        for i, item in enumerate(toc_items):
            # go over all elements between start_el and end_el
            current_element = item.start_el
            while current_element is not None and current_element != item.end_el:
                # Temporary workaround: skip problematic elements
                # if current_element.get('id') in ['f-429-1', 'f-668-1', 'f-685-2', 'f-893-2', 'f-972-1']:
                #     print(f"Skipping problematic element with id: {current_element.get('id')}")
                #     current_element = current_element.find_next_sibling()
                #     continue
                    
                structured_node = self._element_to_structural_node(current_element)
                structured_node.metadata.parent_item = item.item
                structured_node.metadata.item_anchor = item.anchor
                nodes.append(structured_node)
                current_element = current_element.find_next_sibling()

        return nodes

    def _update_nodes_metadata_page_number(self, nodes: List[StructuralNode]) -> None:
        """
        Updates the page metadata for all nodes based on the next PageFooter node after them
        """
        for i, node in enumerate(nodes):
            if node.node_type != "page_footer":
                # Find the next page_footer node after this one
                next_footer = next((n for n in nodes[i:] if n.node_type == "page_footer"), None)
                if next_footer:
                    # PageFooterNode has page_number attribute
                    node.metadata.page_number = getattr(next_footer, 'page_number', None)
            else:
                # For page footer nodes, set their own page number
                node.metadata.page_number = getattr(node, 'page_number', None)
                
    
    def _update_nodes_base_metadata(self, nodes: List[StructuralNode]) -> None:
        """
        Updates the base metadata (company, ticker, form, etc.) for each node
        """
        for node in nodes:
            node.metadata.company = self.company
            node.metadata.ticker = self.ticker
            node.metadata.form = self.form
            node.metadata.filing_date = self.filing_date
            node.metadata.year = self.year
            node.metadata.filing_url = self.filing_url
            node.metadata.period_of_report = self.period_of_report
    @staticmethod
    def _classify_element(element: Tag) -> StructuralNodeType:
        
        # only one of these can be true, assert this
        is_table = extract_table(element) is not None
        is_image = extract_image(element) is not None
        is_page_footer = extract_page_footer(element) is not None
        element_is_non_content = is_non_content(element)

        is_text = extract_text(element) is not None
        
        # only one of these can be true (assumptiona about format)
        if sum([is_table, is_image, is_page_footer, element_is_non_content, is_text]) != 1:
            raise ValueError(f"Multiple element types found: {element.name} - is_table: {is_table}, is_image: {is_image}, is_page_footer: {is_page_footer}, is_non_content: {element_is_non_content}, is_text: {is_text}")
        
        if is_table:
            return "table"
        elif is_image:
            return "image"
        elif is_page_footer:
            return "page_footer"
        elif element_is_non_content:
            return "non_content"
        elif is_text:
            return "text"
        else:
            raise ValueError(f"Unknown element type: {element.name}")
        
    def _element_to_structural_nodes(self, element: Tag) -> List[StructuralNode]:
        try:
            node_type = self._classify_element(element)
        except ValueError:
            nodes = []
            for child in element.children:
                if isinstance(child, Tag):
                    nodes.extend(self._element_to_structural_nodes(child))
            return nodes

        node = self._create_single_node(element, node_type)
        return [node]
    
    def _element_to_structural_node(self, element: Tag) -> StructuralNode:
        """Legacy method - returns first node from the list"""
        nodes = self._element_to_structural_nodes(element)
        return nodes[0] if nodes else NonContentNode.from_element(element)

    def _create_single_node(self, element: Tag, node_type: str) -> StructuralNode:
        """Helper method to create a single structural node"""
        match node_type:
            case "table":
                return TableNode.from_element(element)
            case "image":
                return ImageNode.from_element(element)
            case "page_footer":
                return PageFooterNode.from_element(element)
            case "non_content":
                return NonContentNode.from_element(element)
            case "text":
                return TextNode.from_element(element)
            case _:
                raise ValueError(f"Unknown element type: {node_type}")
                         
    def _get_toc_items(self) -> List[ItemTOCElement]:
        """
        returns a list of TenKItemInfoEnhanced objects, that represent the table of contents of the 10-k filing
        and allowes to get the start and end elements of the item
        """
        toc_table = self._find_toc_table()   

        if toc_table is None:
            raise ValueError("Table of Contents not found in 10-k filing")
        
        # get a tags from table, construct a list of tuples (href, text)
        toc_links = toc_table.find_all("a")
        
        # Pattern to match Item numbers (e.g., "Item 1", "Item 1A", "Item 7A")
        item_pattern = re.compile(r'^(Item|ITEM)\s+(\d+[A-Z]?)', re.IGNORECASE)
        
        # First pass: collect all items with their start elements
        toc_items = []
        item_indices = []  # Track indices of items in toc_links for second pass
        
        for idx, link in enumerate(toc_links):
            link_text = link.get_text(strip=True)
            href = link.get('href', '')
            
            # Check if this link is for an Item
            match = item_pattern.match(link_text)
            if match:
                item_num = match.group(2).upper()  # e.g., "1", "1A", "7"
                item_key = f"Item {item_num}"
                
                # Skip if we don't have info for this item
                if item_key not in ITEMS:
                    continue
                    
                # Get the base info
                base_info = ITEMS[item_key]
                
                # Extract anchor from href (remove the #)
                anchor = href.lstrip('#') if href.startswith('#') else href
                
                # Find the element this anchor points to
                start_el = self._resolve_anchor(self.soup, anchor) if anchor else None
                
                # Create the enhanced info object (end_el will be set in second pass)
                enhanced_info = ItemTOCElement(
                    item=base_info.item,
                    technical_name=base_info.technical_name,
                    display_name=base_info.display_name,
                    description=base_info.description,
                    anchor=anchor,
                    start_el=start_el,
                    end_el=None,  # Will be set in second pass
                    link_text=link_text
                )
                
                toc_items.append(enhanced_info)
                item_indices.append(idx)
        
        # Second pass: determine end elements
        for i, item in enumerate(toc_items):
            if item.start_el:
                # Check if there's a next item
                if i + 1 < len(toc_items):
                    next_item = toc_items[i + 1]
                    if next_item.start_el:
                        # The end element is the element before the next item starts
                        item.end_el = next_item.start_el.find_previous_sibling() or next_item.start_el.parent
                    else:
                        # Next item doesn't have a start element, keep looking
                        for j in range(i + 2, len(toc_items)):
                            future_item = toc_items[j]
                            if future_item.start_el:
                                item.end_el = future_item.start_el.find_previous_sibling() or future_item.start_el.parent
                                break
                
                # If no end element found (last item or no subsequent items with start_el)
                if not item.end_el:
                    # Find the last significant element in the document
                    all_elements = self.soup.find_all(['div', 'table', 'p'])
                    if all_elements:
                        item.end_el = all_elements[-1]
                    else:
                        # Fallback to body or soup
                        item.end_el = self.soup.body or self.soup
        
        return toc_items

    
    def _resolve_anchor(self, soup: BeautifulSoup, anchor: str) -> Optional[Tag]:
        """
        Returns the first element matching id=anchor or name=anchor.
        Fallback: return None if not found.
        """
        return soup.find(id=anchor) or soup.find("a", {"name": anchor})    
        
    def _find_toc_table(self) -> Optional[Tag]:
        """
        Find the table of contents table in the 10-k filing
        """
        
        # Method 1: Find elements containing "Table of Contents" text
        toc_pattern = re.compile(r"table\s+of\s+contents", re.IGNORECASE)
        
        # Look for any element containing this text (not just text nodes)
        for element in self.soup.find_all(text=toc_pattern):
            # Get the parent element that contains this text
            parent = element.parent
            while parent and parent.name not in ['div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                parent = parent.parent
            
            if parent:
                # Look for the next table after this element
                table = parent.find_next("table")
                if table:
                    return table
        
        # Method 2: Look for span/div elements with TOC text
        for tag_name in ['span', 'div', 'p']:
            toc_elements = self.soup.find_all(tag_name, string=toc_pattern)
            for elem in toc_elements:
                # Find the next table
                table = elem.find_next("table")
                if table:
                    return table
        
        # Method 3: If no table found after TOC text, look for table with many Item links
        all_tables = self.soup.find_all("table")
        item_pattern = re.compile(r'Item\s+\d+[A-Z]?', re.IGNORECASE)
        
        best_table = None
        max_item_count = 0
        
        for table in all_tables:
            links = table.find_all("a")
            item_count = sum(1 for link in links if item_pattern.match(link.get_text(strip=True)))
            
            if item_count >= 5 and item_count > max_item_count:
                max_item_count = item_count
                best_table = table
        
        return best_table


def extract_table(element: Tag) -> Optional[Tag]:
    tables = element.find_all("table")
    
    if len(tables) > 1:
        # Get element info without printing entire HTML
        element_info = f"<{element.name}"
        if element.get('id'):
            element_info += f" id='{element.get('id')}'"
        if element.get('class'):
            element_info += f" class='{' '.join(element.get('class'))}'"
        element_info += ">"
        
        raise ValueError(f"Element contains multiple tables ({len(tables)}): {element_info} - First 100 chars: {str(element)[:100]}...")
    
    return tables[0] if len(tables) == 1 else None

def extract_image(element: Tag) -> Optional[Tag]:
    imgs = element.find_all("img")
    
    if len(imgs) > 1:
        raise ValueError(f"Element contains multiple images ({len(imgs)}): {element}")
    
    return imgs[0] if len(imgs) == 1 else None


def extract_page_footer(element: Tag) -> Optional[int]:
    """
    Check if element is a page footer and extract page number.
    
    Returns:
        page_number if it matches, None otherwise
    """
    
    PAGE_FOOTER_PATTERN = re.compile(r"""
    ^\s*                             # optional leading whitespace
    .+?                              # short text (company name, etc.)
    \s*\|\s*                         # separator
    (\d{4})\s+Form\s+10-K            # year + "Form 10-K"
    \s*\|\s*                         # separator
    (\d+)\s*$                         # page number at the end
""", re.VERBOSE)

    # get text from element
    text = element.get_text(" ", strip=True)
    
    match = PAGE_FOOTER_PATTERN.match(text)
    if match:
        year, page_number = match.groups()
        return int(page_number)
    else:
        return None

def is_non_content(element: Tag) -> bool:
    text = element.get_text(strip=True)
    return not text and extract_table(element) is None and extract_image(element) is None and extract_page_footer(element) is None

def extract_text(element: Tag) -> Optional[str]:
    text = element.get_text(strip=True)
    
    if (extract_table(element) is not None 
        or extract_image(element) is not None 
        or extract_page_footer(element) is not None
        or not text):
        return None
    
    return text
