"""This "graph" simply exposes an endpoint for a user to upload docs to be indexed."""

import json
import traceback
from typing import Optional
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from index import TenKChunker
from index_graph.configuration import IndexConfiguration
from index_graph.state import IndexState
from shared import retrieval
from shared.logger import get_logger

logger = get_logger(__name__)

async def chunk(
    state: IndexState, *, config: Optional[RunnableConfig] = None
) -> dict[str, list[Document]]:
    """Fetch and chunk SEC reports into documents.

    This function takes ticker symbols from the state, fetches their SEC filings 
    (type determined by configuration), processes them using our SEC chunker, 
    and converts the chunks to LangChain Documents ready for indexing.

    Args:
        state (IndexState): The current state containing optional SEC tickers.
        config (Optional[RunnableConfig]): Configuration for the processing.

    Returns:
        dict with updated documents list including SEC chunks.
    """
    # Get configuration from config
    configuration = IndexConfiguration.from_runnable_config(config)
    
    # Get SEC filings to process from configuration
    sec_filings = configuration.sec_filings
    logger.info(f"Processing {len(sec_filings)} SEC filings: {[(f.ticker, f.year) for f in sec_filings]}")
    logger.debug(f"Configuration: {configuration}")
    if not sec_filings:
        return {"docs": state.docs or []}

    try:
        # Start with existing docs
        all_docs = list(state.docs or [])
        
        # Process each SEC filing
        for filing in sec_filings:
            try:
                # Chunk the parsed document (this internally parses the SEC filing)
                chunker = TenKChunker(filing.ticker, filing.year)
                chunks = chunker.get_chunks()
                
                # Log detailed chunk statistics
                statistics = chunker.get_statistics(chunks)
                logger.info(f"Created {statistics.total_chunks} chunks for {filing.ticker} ({filing.year})")
                logger.debug(f"Chunking statistics: {json.dumps(statistics.model_dump(), indent=2)}")
                
                # convert chunks to Lanchain Documents
                for chunk in chunks:
                    document = Document(
                        page_content=chunk.content, # this is whats going to be embedded
                        metadata=chunk.metadata.model_dump() # this is whats going to be used for retrieval filtering
                    )
                    all_docs.append(document)
                
            except Exception as e:
                logger.error(f"Error processing {filing.ticker} ({filing.year}): {e}")
                logger.error(f"Stack trace:\n{traceback.format_exc()}")
                # Continue with other filings even if one fails
                continue
        
        # throw error to prevent further processing during debugging
        # raise Exception("Debugging mode enabled, stopping further processing.")
    
        return {"docs": all_docs}
        
    except ImportError as e:
        logger.error(f"SEC chunker dependencies not available: {e}")
        # Return existing docs if SEC processing fails
        return {"docs": state.docs or []}


async def index_docs(
    state: IndexState, *, config: Optional[RunnableConfig] = None
) -> dict[str, str]:
    """Asynchronously index documents in the given state using the configured retriever.

    This function takes the documents from the state, ensures they have a user ID,
    adds them to the retriever's index, and then signals for the documents to be
    deleted from the state.

    If docs are not provided in the state, they will be loaded
    from the configuration.docs_file JSON file.

    Args:
        state (IndexState): The current state containing documents and retriever.
        config (Optional[RunnableConfig]): Configuration for the indexing process.r
    """
    
    docs = state.docs

    with retrieval.make_vector_store(config) as vector_store:
        try:
            await vector_store.adelete_collection()
            logger.info("Successfully cleared existing documents")
        except Exception as e:
            logger.warning(f"Could not clear existing documents: {e}")
    
    logger.debug(f"Embedding {len(docs)} new documents")
    
    try:
        with retrieval.make_retriever(config) as retriever:
            await retriever.aadd_documents(docs)
        logger.info(f"Successfully added {len(docs)} documents.")
    except Exception as e:
        logger.error(f"Failed to add documents to vector store: {e}")
        logger.error(f"Stack trace:\n{traceback.format_exc()}")
        raise
    # causes reducer to delete docs from state
    return {"docs": "delete"}


# Define the graph
builder = StateGraph(IndexState, config_schema=IndexConfiguration)
builder.add_node("chunk", chunk)
builder.add_node("index_docs", index_docs)
builder.add_edge(START, "chunk")
builder.add_edge("chunk", "index_docs")
builder.add_edge("index_docs", END)
# Compile into a graph object that you can invoke and deploy.
graph = builder.compile()
graph.name = "IndexGraph"
