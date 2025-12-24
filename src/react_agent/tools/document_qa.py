"""Document QA tool for searching indexed documents in the RAG system."""

from typing import Annotated, Any, Optional, cast

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from shared import retrieval


@tool(parse_docstring=True)
async def document_qa(
    query: Annotated[str, "The question to search for in the indexed documents"],
    k: Annotated[int, "Number of documents to retrieve"] = 5,
    *,
    config: Annotated[RunnableConfig, InjectedToolArg]
) -> Optional[list[dict[str, Any]]]:
    """Search through 10-k filings for relevant information.
    Use this tool when you need:
    
    Args:
        query: The search query/question
        k: Number of relevant documents to retrieve (default: 5)
        
    """
    try:
        # Get the retriever using the shared retrieval module
        with retrieval.make_retriever(config) as retriever:
            # Perform the search asynchronously
            # Note: retriever.ainvoke typically just takes the query string
            # The k parameter is handled by limiting results after retrieval
            docs = await retriever.ainvoke(query)
            
            # Limit to k documents
            if len(docs) > k:
                docs = docs[:k]
            
            if not docs:
                docs = []
            
            # Build structured results
            results = []
            for doc in docs:
                metadata = doc.metadata or {}
                
                # Extract all metadata fields
                result = {
                    "chunk_id_for_citations": metadata.get("uuid"),
                    "content": doc.page_content,
                    "source": {
                        "company": metadata.get("company"),
                        "ticker": metadata.get("ticker"),
                        "form": metadata.get("form"),
                        "data_valid_until": metadata.get("period_of_report"),
                        "item": metadata.get("item"),
                        "item_title": metadata.get("item_title"),
                        "table_references": metadata.get("table_references"),
                        "image_references": metadata.get("image_references"),      
                    }
                }
                
                # Remove None values to keep the JSON clean
                result = {k: v for k, v in result.items() if v is not None}
                
                results.append(result)
            
            return cast(list[dict[str, Any]], results)
            
    except Exception as e:
        # Return error in structured format
        return [{"error": f"Error searching documents: {str(e)}"}]

