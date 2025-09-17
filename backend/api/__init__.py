"""
API layer for the FAQ bot.
"""

from .dependencies import get_faq_manager, get_vector_store, get_claude_client
from .error_handlers import register_error_handlers

__all__ = [
    "get_faq_manager",
    "get_vector_store",
    "get_claude_client",
    "register_error_handlers",
]
