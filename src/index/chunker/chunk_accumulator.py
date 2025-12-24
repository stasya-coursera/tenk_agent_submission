from typing import List, Optional
import uuid

from index.parser.types import StructuralNode
from .types import Chunk, ChunkMetadata, ChunkType, ItemChunkingConfig


class ChunkAccumulator:
    """Accumulates text and nodes into properly sized chunks with overlap support."""
    
    def __init__(self, config: ItemChunkingConfig, before_overlap_accumulator: Optional['ChunkAccumulator'] = None):
        self.config = config
        self.current_nodes: List[StructuralNode] = []
        # Budget is max_chunk_size (core content without overlap)
        self.budget = config.max_chunk_size_words
        self.before_overlap_accumulator = before_overlap_accumulator
        self.after_overlap_accumulator: Optional['ChunkAccumulator'] = None
        self.current_content_size = 0
        
    def _can_add(self, node: StructuralNode) -> bool:
        """Check if a node can be added without exceeding the budget."""
        node_size = self._get_node_size(node)
        return self.current_content_size + node_size <= self.budget
    
    def _get_node_size(self, node: StructuralNode) -> int:
        """Get the word count size of a node."""
        node_text = getattr(node, 'text', '')
        return len(node_text.split())
    
    def _add_node(self, node: StructuralNode) -> None:
        """Add a node to the accumulator and update size tracking."""
        node_size = self._get_node_size(node)
        self.current_nodes.append(node)
        self.current_content_size += node_size
    
    def add(self, node: StructuralNode) -> bool:
        """Attempt to add a node to the current chunk."""
        if not self._can_add(node):
            return False
        
        self._add_node(node)
        return True
    
    def set_before_overlap_accumulator(self, accumulator: 'ChunkAccumulator') -> None:
        self.before_overlap_accumulator = accumulator
    
    def set_after_overlap_accumulator(self, accumulator: 'ChunkAccumulator') -> None:
        self.after_overlap_accumulator = accumulator
    
    def get_start(self, word_count: int) -> str:
        """Get overlap content from the start of this accumulator.
        For tables/images at start, use min_text regardless of word count.
        """
        if not self.current_nodes:
            return ""
        
        first_node = self.current_nodes[0]
        
        # If first node is table/image, use min_text
        if first_node.node_type in ["table", "image"] and hasattr(first_node, 'min_text'):
            return first_node.min_text
        
        # Otherwise use word-based overlap from start
        all_text = []
        for node in self.current_nodes:
            if hasattr(node, 'text') and node.text.strip():
                all_text.append(node.text.strip())
        
        if not all_text:
            return ""
        
        combined_text = "\n\n".join(all_text)
        words = combined_text.split()
        start_words = words[:word_count] if len(words) > word_count else words
        return " ".join(start_words)
    
    def get_end(self, word_count: int) -> str:
        """Get overlap content from the end of this accumulator.
        For tables/images at end, use min_text regardless of word count.
        """
        if not self.current_nodes:
            return ""
        
        last_node = self.current_nodes[-1]
        
        # If last node is table/image, use min_text
        if last_node.node_type in ["table", "image"] and hasattr(last_node, 'min_text'):
            return last_node.min_text
        
        # Otherwise use word-based overlap from end
        all_text = []
        for node in self.current_nodes:
            if hasattr(node, 'text') and node.text.strip():
                all_text.append(node.text.strip())
        
        if not all_text:
            return ""
        
        combined_text = "\n\n".join(all_text)
        words = combined_text.split()
        end_words = words[-word_count:] if len(words) > word_count else words
        return " ".join(end_words)
    
    def _collect_content(self) -> str:
        """Collect all content parts into a single string with proper overlap handling."""
        content_parts = []
        
        # Add before overlap using get_end() from previous accumulator
        if self.before_overlap_accumulator:
            overlap_content = self.before_overlap_accumulator.get_end(self.config.chunk_overlap_words)
            if overlap_content.strip():
                content_parts.append(overlap_content.strip())
            
        # Add current nodes content
        for node in self.current_nodes:
            if hasattr(node, 'text') and node.text.strip():
                content_parts.append(node.text.strip())
                
        # Add after overlap using get_start() from next accumulator
        if self.after_overlap_accumulator:
            overlap_content = self.after_overlap_accumulator.get_start(self.config.chunk_overlap_words)
            if overlap_content.strip():
                content_parts.append(overlap_content.strip())
            
        return "\n\n".join(content_parts)
    
    def _collect_references(self) -> tuple[List[str], List[str]]:
        """Collect table and image references from nodes and overlap accumulators."""
        table_refs = []
        image_refs = []
        
        # Collect from current nodes
        for node in self.current_nodes:
            if node.node_type == "table" and node.metadata.structural_node_id:
                table_refs.append(node.metadata.structural_node_id)
            elif node.node_type == "image" and node.metadata.structural_node_id:
                image_refs.append(node.metadata.structural_node_id)
        
        # Collect from overlap accumulators 
        for overlap_acc in [self.before_overlap_accumulator, self.after_overlap_accumulator]:
            if overlap_acc:
                for node in overlap_acc.current_nodes:
                    if node.node_type == "table" and node.metadata.structural_node_id:
                        table_refs.append(node.metadata.structural_node_id)
                    elif node.node_type == "image" and node.metadata.structural_node_id:
                        image_refs.append(node.metadata.structural_node_id)
        
        # Remove duplicates while preserving order
        table_refs = list(dict.fromkeys(table_refs))
        image_refs = list(dict.fromkeys(image_refs))
        
        return table_refs, image_refs
    
    def _collect_page_info(self) -> tuple[List[str], Optional[tuple[str, str]]]:
        """Collect page numbers and create page range."""
        page_numbers = set()
        
        for node in self.current_nodes:
            if node.metadata.page_number:
                page_numbers.add(str(node.metadata.page_number))
                
        page_range = None
        if page_numbers:
            sorted_pages = sorted(page_numbers, key=int)
            # Always create a range, even for single pages (x to x)
            page_range = (sorted_pages[0], sorted_pages[-1])
                
        return sorted(page_numbers, key=int) if page_numbers else [], page_range
    
    def _collect_structural_node_ids(self) -> List[str]:
        """Collect all structural node IDs."""
        return [node.metadata.structural_node_id for node in self.current_nodes 
                if node.metadata.structural_node_id]
    
    def to_chunk(self) -> Chunk:
        """Create a chunk from the accumulated nodes with overlap text."""
        if not self.current_nodes:
            raise ValueError("Cannot create chunk from empty accumulator")
            
        content = self._collect_content()
        table_refs, image_refs = self._collect_references()
        page_numbers, page_range = self._collect_page_info()
        structural_node_ids = self._collect_structural_node_ids()
        
        # Get item and filing metadata from first node (assuming all nodes are from same item and filing)
        first_node_metadata = self.current_nodes[0].metadata if self.current_nodes else None
        item = first_node_metadata.parent_item if first_node_metadata else None
        item_anchor = first_node_metadata.item_anchor if first_node_metadata else None
        
        metadata = ChunkMetadata(
            chunk_type=ChunkType.REGULAR,
            item=item,
            item_anchor=item_anchor,
            page_numbers=page_numbers if page_numbers else None,
            page_range=page_range,
            table_references=table_refs if table_refs else None,
            image_references=image_refs if image_refs else None,
            structural_node_ids=structural_node_ids,
            company=first_node_metadata.company if first_node_metadata else None,
            ticker=first_node_metadata.ticker if first_node_metadata else None,
            form=first_node_metadata.form if first_node_metadata else None,
            period_of_report=first_node_metadata.period_of_report if first_node_metadata else None,
            year=first_node_metadata.year if first_node_metadata else None,
            filing_url=first_node_metadata.filing_url if first_node_metadata else None
        )
        
        chunk_id = f"chunk_{uuid.uuid4().hex[:8]}"
        
        return Chunk(
            id=chunk_id,
            content=content,
            metadata=metadata
        )
