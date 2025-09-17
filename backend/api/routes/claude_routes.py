"""
Claude AI query route matching original app.py endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from models import QueryRequest
from core.claude_client import ClaudeClient
from core.vector_store import VectorStore
from api.dependencies import get_claude_client, get_vector_store
import json
import asyncio
from datetime import datetime

router = APIRouter(tags=["Claude AI"])


@router.post("/query-with-rag")
async def query_with_rag(
    request: QueryRequest,
    claude_client: ClaudeClient = Depends(get_claude_client),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Generate AI response using RAG context with streaming."""
    if not claude_client.is_ready():
        raise HTTPException(status_code=503, detail="System is still initializing")

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    retrieved_context = vector_store.search_similar_faqs(
        request.message, top_k=request.top_k
    )

    async def generate_stream():
        try:
            # Generate Claude response with streaming
            async for chunk in claude_client.ask_with_context_stream(
                message=request.message,
                top_k=request.top_k,
                conversation_history=request.conversationHistory,
                retrieved_context=retrieved_context,
            ):
                # The chunk is already formatted as SSE from claude_client
                yield chunk

                # Add small delay for better streaming experience
                await asyncio.sleep(0.01)

        except Exception as e:
            error_data = {
                "type": "error",
                "text": f"Query error: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )
