"""Validate and format citations in agent responses."""

import re
from typing import Optional

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from react_agent.state import ReactGraphAnnotation
from shared import retrieval


def _should_validate_citation(chunk_id: str) -> bool:
    """Determine if a citation should be validated against the database.
    
    Skip validation for web search citations and only validate database chunk IDs.
    """
    # Skip simple numbers (likely web search result references)
    if chunk_id.isdigit():
        return False
    
    # Skip URLs
    if chunk_id.startswith(('http://', 'https://', 'www.')):
        return False
        
    # Skip very short citations (likely web search references)
    if len(chunk_id) < 10:
        return False
    
    # Validate citations that look like UUIDs or database IDs
    # (longer strings with hyphens, underscores, or alphanumeric patterns)
    return True


async def get_chunk_by_id(chunk_id: str, config: RunnableConfig) -> Optional[dict]:
    """Retrieve a specific chunk by its ID from the vector store."""
    try:
        with retrieval.make_vector_store(config) as vstore:
            # Use similarity search with the chunk_id as metadata filter
            docs = await vstore.asimilarity_search(
                "", 
                k=1,
                filter={"uuid": chunk_id}
            )
            
            if docs:
                doc = docs[0]
                metadata = doc.metadata or {}
                return {
                    "chunk_id": metadata.get("id"),
                    "content": doc.page_content,
                    "company": metadata.get("company"),
                    "ticker": metadata.get("ticker"),
                    "form": metadata.get("form"),
                    "item": metadata.get("item"),
                    "item_title": metadata.get("item_title"),
                    "filing_url": metadata.get("filing_url"),
                    "item_anchor": metadata.get("item_anchor"),
                    "page_range": metadata.get("page_range"),
                    "period_of_report": metadata.get("period_of_report"),
                }
    except Exception as e:
        print(f"Error retrieving chunk {chunk_id}: {str(e)}")
    
    return None


def format_citation_link(chunk_id: str, chunk_data: dict) -> str:
    """Format a citation as a link with readable text but linking to the URL."""
    item = chunk_data.get("item", "Unknown")
    page_range = chunk_data.get("page_range", "Unknown")
    filing_url = chunk_data.get("filing_url", "")
    item_anchor = chunk_data.get("item_anchor", "")
    
    # Construct the full URL with anchor if available
    if filing_url and item_anchor:
        full_url = f"{filing_url}#{item_anchor}"
    else:
        full_url = filing_url or "#"
    
    # Format as markdown link with readable text (item | page) but keep chunk_id reference
    # if page range starts and end with the same number, only show the number
    if page_range[0] == page_range[1]:
        link_text = f"{item} | page {page_range[0]}"
    else:
        link_text = f"{item} | pages {page_range[0]}-{page_range[1]}"
        
    link_text = f"{item} | pages {page_range}"
    return f"[{link_text}]({full_url})"


async def validate_citations(
    state: ReactGraphAnnotation, config: RunnableConfig
) -> dict[str, list[AIMessage]]:
    """Validate citations in the last AI message and format them as links.
    
    This function:
    1. Finds all [@chunk_id] citations in the last AI message
    2. Retrieves each chunk from the database to verify it exists
    3. Replaces valid citations with formatted links [@chunk_id | <item> | <page_range>]
    4. Removes or marks invalid citations
    
    Args:
        state (ReactGraphAnnotation): The current state of the react graph.
        config (RunnableConfig): The configuration for running the model.
        
    Returns:
        dict[str, list[AIMessage]]: Updated state with validated citations.
    """
    if not state.messages:
        return {"messages": []}
    
    last_message = state.messages[-1]
    
    # Only process AI messages
    if not isinstance(last_message, AIMessage):
        return {"messages": []}
    
    content = last_message.content
    if not content:
        return {"messages": []}
    
    # Find all citation patterns [@chunk_id]
    citation_pattern = r'\[@([^\]]+)\]'
    citations = re.findall(citation_pattern, content)
    
    if not citations:
        # No citations found, return the original message as is
        return {"messages": [last_message]}
    
    # Process each citation
    updated_content = content
    for chunk_id in set(citations):  # Use set to avoid duplicates
        # Skip validation for citations that don't look like database chunk IDs
        # Only validate if chunk_id looks like a UUID or database ID format
        # Skip web search citations (numbers, URLs, etc.)
        if not _should_validate_citation(chunk_id):
            continue
            
        chunk_data = await get_chunk_by_id(chunk_id, config)
        
        if chunk_data:
            # Valid citation - replace with formatted link
            old_citation = f"[@{chunk_id}]"
            new_citation = format_citation_link(chunk_id, chunk_data)
            updated_content = updated_content.replace(old_citation, new_citation)
        else:
            # Invalid citation - mark as invalid or remove
            old_citation = f"[@{chunk_id}]"
            invalid_citation = f"[@{chunk_id} - INVALID]"
            updated_content = updated_content.replace(old_citation, invalid_citation)
    
    # Combine original and validated content with a separator
    # combined_content = f"{content}\n\n---\n\nVALIDATED VERSION:\n{updated_content}"
    
    # Create new AI message with combined content
    updated_message = AIMessage(
        content=updated_content,
        id=last_message.id,
        tool_calls=last_message.tool_calls,
        additional_kwargs=last_message.additional_kwargs,
    )
    
    # Return the updated messages, replacing the last message
    updated_messages = state.messages[:-1] + [updated_message]
    
    return {"messages": updated_messages}
