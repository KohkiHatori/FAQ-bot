from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


# Pydantic models for API request/response
class QueryRequest(BaseModel):
    message: str
    conversationHistory: str = ""
    top_k: int = 3


class CacheInfoResponse(BaseModel):
    cached: bool
    cache_dir: Optional[str] = None
    metadata: Optional[dict] = None
    file_sizes: Optional[dict] = None
    error: Optional[str] = None


class CacheActionResponse(BaseModel):
    success: bool
    message: str
    timestamp: str


# FAQ Management Models
class FAQResponse(BaseModel):
    id: int
    question: str
    answer: str
    status: str = "public"
    category: str = "other"
    tags: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FAQListResponse(BaseModel):
    faqs: List[FAQResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class FAQCreateRequest(BaseModel):
    question: str
    answer: str
    status: str = "public"
    category: str = "other"
    tags: List[str] = []

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in ["public", "private", "pending"]:
            raise ValueError('status must be "public", "private", or "pending"')
        return v


class FAQUpdateRequest(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ["public", "private", "pending"]:
            raise ValueError('status must be "public", "private", or "pending"')
        return v


class FAQCreateResponse(BaseModel):
    success: bool
    message: str
    faq: Optional[FAQResponse] = None
    timestamp: str


class FAQUpdateResponse(BaseModel):
    success: bool
    message: str
    faq: Optional[FAQResponse] = None
    old_faq: Optional[FAQResponse] = None
    timestamp: str


class FAQDeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_faq: Optional[FAQResponse] = None
    timestamp: str


# Pending Changes Models
class PendingChangeResponse(BaseModel):
    faq_id: int
    change_type: str
    original_status: Optional[str] = None
    timestamp: str


class PendingChangesResponse(BaseModel):
    changes: List[PendingChangeResponse]
    total_count: int
    stats: dict
    has_pending: bool
    timestamp: str


class StatusRestoreResponse(BaseModel):
    success: bool
    restored_count: int
    cleared_count: int
    timestamp: str
