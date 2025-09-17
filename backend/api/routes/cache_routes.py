"""
Cache-related API routes matching original app.py endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, Query
from models import CacheInfoResponse, CacheActionResponse
from core.vector_store import VectorStore
from core.faq import FAQManager
from api.dependencies import get_vector_store, get_faq_manager
from datetime import datetime

router = APIRouter(tags=["Cache"])


@router.get("/cache", response_model=CacheInfoResponse)
async def get_cache_info(vector_store: VectorStore = Depends(get_vector_store)):
    """Get RAG cache information."""
    cache_info = vector_store.get_cache_info()

    # Map VectorStore response to CacheInfoResponse model
    if cache_info.get("cached", False):
        # When cache exists, build metadata from VectorStore fields
        metadata = {
            "model_name": cache_info.get("model_name"),
            "document_count": cache_info.get("document_count"),
            "embedding_dimension": cache_info.get("embedding_dimension"),
            "distance_metric": cache_info.get("distance_metric"),
            "created_at": cache_info.get("created_at"),
            "timestamp": cache_info.get("timestamp"),
        }

        return CacheInfoResponse(
            cached=True,
            cache_dir=cache_info.get("cache_dir"),
            metadata=metadata,
            file_sizes=None,  # VectorStore doesn't provide file sizes
            error=None,
        )
    else:
        # When cache doesn't exist or has error
        return CacheInfoResponse(
            cached=False,
            cache_dir=None,
            metadata={},
            file_sizes=None,
            error=cache_info.get("message", "Cache not available"),
        )


@router.post("/cache/rebuild", response_model=CacheActionResponse)
async def rebuild_cache(
    vector_store: VectorStore = Depends(get_vector_store),
    faq_manager: FAQManager = Depends(get_faq_manager),
):
    """Rebuild RAG cache with current FAQ data."""
    result = vector_store.rebuild_cache(faq_manager)

    return CacheActionResponse(
        success=result["success"],
        message=result["message"],
        timestamp=datetime.now().isoformat(),
    )
