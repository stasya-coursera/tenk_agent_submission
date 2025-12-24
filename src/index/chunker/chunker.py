import json
from typing import List
import uuid
from shared.logger import get_logger
from index.parser.parser import TenKParser
from index.parser.types import ItemView, StructuralNode
from index.constants import ITEMS
from .types import Chunk, ItemChunkingConfig, ITEMS_CHUNKING_CONFIGS, ChunkStatistics, ItemStatistics
from .chunk_accumulator import ChunkAccumulator

logger = get_logger(__name__)

"""
Decides what chunks to create based on the structured nodes
"""

class TenKChunker:
    def __init__(self, ticker: str, year: int):
        self.ticker = ticker
        self.year = year

    def get_chunks(self) -> List[Chunk]:
        parser = TenKParser.from_ticker_year(self.ticker, self.year)
        nodes = parser.get_structured_nodes_stream()
        # mytable = nodes[252]
        
        # # print table metadata - columns
        # print(f"Columns: {mytable.table_metadata.column_names}")
        # # print table metadata - rows
        # print(f"Rows: {mytable.table_metadata.row_names}")
        
        # print mytable.table_lookup.data, with value for each ke
        # for key, value in mytable.table_lookup.data.items():
        #     print(f"{key} -> {value}")
        #     print("--------------------------------")


        semantic_document = parser.get_semantic_document(nodes)
        
        logger.info(f"Chunking for {self.ticker} in {self.year}")
        chunks = []
        for item in semantic_document:
            item_chunks = self._merge_structural_nodes_into_chunks(item)
            chunks.extend(item_chunks)
        
        
        # Set global order for all chunks
        for i, chunk in enumerate(chunks):
            chunk.metadata.order = i
        
        statistics = self.get_statistics(chunks)
        
        logger.info(f"Successfully created {len(chunks)} chunks for {self.ticker} in {self.year}") 
        logger.debug(f"Chunking statistics: {json.dumps(statistics.model_dump(), indent=2)}")
                   
        return chunks
    
    def _merge_structural_nodes_into_chunks(self, item: ItemView) -> List[Chunk]:
        """

        Chunking strategy

        if a node.text can be added to a chunk in its entirety - add it
        if a node.text cant be added in its entirety, but can be made into its own chunk => make its own chunk
        if a node.text is too large to be a single chunk - split it semantically (lets do this later, for now just create a single node for it, even though it violated the size and issue a warning to log

        this logic is the same for all types of nodes (Text / Table / Image). 

        but overlap logic is different for image / table

        when we need to overlap with a table or image, we dont take a substring of the text, but the entire min_text property of the node, even if this means we exceed the chunk size.
        We also add the table / image reference to the metadata of botht the node with the overlap, and the actual table node. 

        """
        if not item.nodes:
            return []
            
        # Get chunking config for this item
        item_config = ITEMS_CHUNKING_CONFIGS.get(item.item)
        if not item_config:
            return []
            
        # Get item info for metadata
        item_info = ITEMS.get(item.item)
            
        # First, create list of accumulators
        accumulators = []
        current_accumulator = ChunkAccumulator(item_config)
        
        for node in item.nodes:
            # Skip non-content nodes like page footers
            if node.node_type in ["page_footer", "non_content"]:
                continue
            
            # Unified chunking strategy for all node types:
            # 1. Try to add node to current accumulator
            if current_accumulator.add(node):
                continue  # Successfully added, move to next node
            
            # 2. Node doesn't fit in current accumulator
            # Finalize current accumulator if it has content
            if current_accumulator.current_nodes:
                accumulators.append(current_accumulator)
                current_accumulator = ChunkAccumulator(item_config)
            
            # 3. Try to add node to new empty accumulator
            if current_accumulator.add(node):
                continue  # Successfully added to new accumulator
            
            # 4. Node is too large even for empty accumulator - force add it and warn
            accumulators.extend(self._split_node_to_multiple_accumulators(node, item_config))
        
        # Add final accumulator if it has content
        if current_accumulator.current_nodes:
            accumulators.append(current_accumulator)
        
        # Set up overlap relationships between accumulators
        for i, accumulator in enumerate(accumulators):
            if i > 0 and item_config.chunk_overlap_words > 0:
                accumulator.set_before_overlap_accumulator(accumulators[i-1])
            if i < len(accumulators) - 1 and item_config.chunk_overlap_words > 0:
                accumulator.set_after_overlap_accumulator(accumulators[i+1])
        
        # Convert accumulators to chunks
        chunks = []
        for i, accumulator in enumerate(accumulators):
            chunk = accumulator.to_chunk()
            chunk.id = f"{item.item}_{i}_{uuid.uuid4().hex[:8]}"
            
            # Populate item title and description from item info
            if item_info:
                chunk.metadata.item_title = item_info.display_name
                chunk.metadata.item_description = item_info.description
            
            chunks.append(chunk)
            
        return chunks
    
    def get_statistics(self, chunks: List[Chunk]) -> ChunkStatistics:
        """Get detailed statistics about the created chunks, organized by item."""
        if not chunks:
            return ChunkStatistics(
                total_chunks=0,
                total_words=0,
                overall_min_words=0,
                overall_max_words=0,
                overall_avg_words=0.0,
                number_of_unique_items=0,
                items={}
            )
        
        from collections import defaultdict
        
        # Calculate overall statistics
        total_words = sum(len(chunk.content.split()) for chunk in chunks)
        content_lengths = [len(chunk.content.split()) for chunk in chunks]
        min_words = min(content_lengths) if content_lengths else 0
        max_words = max(content_lengths) if content_lengths else 0
        avg_words = total_words / len(chunks) if chunks else 0
        
        # Group statistics by item
        item_stats = defaultdict(lambda: {
            'chunk_count': 0,
            'total_words': 0,
            'word_lengths': [],
            'table_chunks': 0,
            'total_tables': 0,
            'image_chunks': 0,
            'total_images': 0
        })
        
        for chunk in chunks:
            if chunk.metadata.item:
                item = chunk.metadata.item
                word_count = len(chunk.content.split())
                
                # Basic statistics
                item_stats[item]['chunk_count'] += 1
                item_stats[item]['total_words'] += word_count
                item_stats[item]['word_lengths'].append(word_count)
                
                # Table statistics
                if chunk.metadata.table_references:
                    item_stats[item]['table_chunks'] += 1
                    item_stats[item]['total_tables'] += len(chunk.metadata.table_references)
                
                # Image statistics  
                if chunk.metadata.image_references:
                    item_stats[item]['image_chunks'] += 1
                    item_stats[item]['total_images'] += len(chunk.metadata.image_references)
        
        # Build structured result
        items = {}
        for item, stats in item_stats.items():
            item_min = min(stats['word_lengths']) if stats['word_lengths'] else 0
            item_max = max(stats['word_lengths']) if stats['word_lengths'] else 0
            item_avg = stats['total_words'] / stats['chunk_count'] if stats['chunk_count'] else 0
            
            items[item] = ItemStatistics(
                chunk_count=stats['chunk_count'],
                total_words=stats['total_words'],
                min_words=item_min,
                max_words=item_max,
                avg_words=item_avg,
                table_chunks=stats['table_chunks'],
                total_tables=stats['total_tables'],
                image_chunks=stats['image_chunks'],
                total_images=stats['total_images']
            )
        
        return ChunkStatistics(
            total_chunks=len(chunks),
            total_words=total_words,
            overall_min_words=min_words,
            overall_max_words=max_words,
            overall_avg_words=avg_words,
            number_of_unique_items=len(items),
            items=items
        )
    
    def _split_node_to_multiple_accumulators(self, node: StructuralNode, item_config: ItemChunkingConfig) -> List[ChunkAccumulator]:
        """
        Split a node into multiple accumulators if it is too large to be a single chunk.
        """
        
        accumulator = ChunkAccumulator(item_config)
        node_size = len(getattr(node, 'text', '').split())
        logger.warning(f"Node {node.metadata.structural_node_id} is too large for chunk size limit. "
                      f"Node size: {node_size} words, max chunk size: {item_config.max_chunk_size_words} words. "
                      f"Adding anyway. Implement splitting logic here in future.")
        accumulator._add_node(node)
        
        return [accumulator]
