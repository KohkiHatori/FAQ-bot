"""
Health check and root routes matching original app.py endpoints.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from core.faq import FAQManager
from core.vector_store import VectorStore
from core.claude_client import ClaudeClient
from api.dependencies import get_faq_manager, get_vector_store, get_claude_client

router = APIRouter(tags=["Health"])


@router.get("/")
async def root(
    vector_store: VectorStore = Depends(get_vector_store),
    claude_client: ClaudeClient = Depends(get_claude_client),
):
    """Root endpoint with system information."""
    system_ready = vector_store.is_ready() and claude_client.is_ready()

    if not system_ready:
        return {
            "message": "RAG FAQ Bot API",
            "status": "initializing",
            "version": "2.0.0",
        }

    return {
        "message": "RAG FAQ Bot API",
        "status": "ready",
        "version": "2.0.0",
        "model": "Claude Sonnet 4",
        "data_source": "SQLite",
        "endpoints": {
            "faqs": "/faqs - List all FAQs with pagination and filtering (status, category, tag)",
            "create": "POST /faqs - Create a new FAQ with status, category, and tags",
            "update": "PUT /faqs/{id} - Update an existing FAQ including status, category, and tags",
            "delete": "DELETE /faqs/{id} - Delete an FAQ",
            "query": "/query-with-rag - AI-powered responses with RAG context",
        },
    }


@router.get("/health")
async def health_check(
    vector_store: VectorStore = Depends(get_vector_store),
    claude_client: ClaudeClient = Depends(get_claude_client),
):
    """Health check endpoint."""
    system_ready = vector_store.is_ready() and claude_client.is_ready()

    return {
        "status": "healthy" if system_ready else "initializing",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "rag_manager": vector_store.is_ready(),
            "claude_handler": claude_client.is_ready(),
            "system_ready": system_ready,
        },
    }
