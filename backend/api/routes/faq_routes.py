"""
FAQ-related API routes matching original app.py endpoints.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from models import (
    FAQResponse,
    FAQCreateRequest,
    FAQUpdateRequest,
    FAQListResponse,
    FAQCreateResponse,
    FAQUpdateResponse,
    FAQDeleteResponse,
    PendingChangesResponse,
)
from core.faq import FAQManager
from core.vector_store import VectorStore
from api.dependencies import get_faq_manager, get_vector_store

router = APIRouter(tags=["FAQs"])


@router.get("/faqs", response_model=FAQListResponse)
async def get_faqs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    faq_manager: FAQManager = Depends(get_faq_manager),
):
    """Get all FAQs with optional filtering and pagination."""
    result = faq_manager.get_faqs(
        limit=limit, offset=offset, status=status, category=category, tag=tag
    )

    return FAQListResponse(
        faqs=result["faqs"],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
        has_more=result["has_more"],
    )


@router.post("/faqs", response_model=FAQCreateResponse)
async def create_faq(
    request: FAQCreateRequest,
    faq_manager: FAQManager = Depends(get_faq_manager),
):
    """Create a new FAQ."""
    faq = faq_manager.create_faq(request)

    return FAQCreateResponse(
        success=True,
        message="FAQ created successfully (pending vector embedding)",
        faq=faq,
        timestamp=datetime.now().isoformat(),
    )


@router.put("/faqs/{faq_id}", response_model=FAQUpdateResponse)
async def update_faq(
    faq_id: int,
    request: FAQUpdateRequest,
    faq_manager: FAQManager = Depends(get_faq_manager),
):
    """Update an existing FAQ."""
    updated_faq, old_faq = faq_manager.update_faq(faq_id, request)

    return FAQUpdateResponse(
        success=True,
        message="FAQ updated successfully (pending vector embedding)",
        faq=updated_faq,
        old_faq=old_faq,
        timestamp=datetime.now().isoformat(),
    )


@router.delete("/faqs/{faq_id}", response_model=FAQDeleteResponse)
async def delete_faq(
    faq_id: int,
    faq_manager: FAQManager = Depends(get_faq_manager),
):
    """Delete an FAQ."""
    deleted_faq = faq_manager.delete_faq(faq_id)

    return FAQDeleteResponse(
        success=True,
        message="FAQ deleted successfully (pending vector cache cleanup)",
        deleted_faq=deleted_faq,
        timestamp=datetime.now().isoformat(),
    )


@router.get("/faqs/tags")
async def get_all_tags(faq_manager: FAQManager = Depends(get_faq_manager)):
    """Get all unique tags."""
    return faq_manager.get_all_tags()


@router.get("/faqs/categories")
async def get_all_categories(faq_manager: FAQManager = Depends(get_faq_manager)):
    """Get all unique categories."""
    return faq_manager.get_all_categories()


@router.get("/faqs/pending", response_model=PendingChangesResponse)
async def get_pending_changes(faq_manager: FAQManager = Depends(get_faq_manager)):
    """Get pending changes that need vector embedding."""
    return faq_manager.get_pending_changes()
