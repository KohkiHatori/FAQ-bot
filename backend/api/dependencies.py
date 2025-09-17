"""
Dependency injection for API services.
"""

from functools import lru_cache
from core.database import db_manager
from core.claude_client import ClaudeClient
from core.vector_store import VectorStore
from core.faq import FAQManager
from core.pending_changes import PendingChangesManager


@lru_cache()
def get_faq_manager() -> FAQManager:
    """Get FAQ manager instance."""
    return FAQManager(db_manager)


# Backward compatibility aliases
def get_faq_service() -> FAQManager:
    """Get FAQ service instance (backward compatibility)."""
    return get_faq_manager()


def get_faq_repository() -> FAQManager:
    """Get FAQ repository instance (backward compatibility)."""
    return get_faq_manager()


@lru_cache()
def get_vector_store() -> VectorStore:
    """Get vector store instance."""
    return VectorStore()


@lru_cache()
def get_claude_client() -> ClaudeClient:
    """Get Claude client instance."""
    return ClaudeClient()


@lru_cache()
def get_pending_changes_manager() -> PendingChangesManager:
    """Get pending changes manager instance."""
    return PendingChangesManager()
