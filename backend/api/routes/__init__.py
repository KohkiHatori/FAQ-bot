"""
API routes for the FAQ bot.
"""

from .faq_routes import router as faq_router
from .cache_routes import router as cache_router
from .claude_routes import router as claude_router
from .health_routes import router as health_router

__all__ = [
    "faq_router",
    "cache_router",
    "claude_router",
    "health_router",
]
