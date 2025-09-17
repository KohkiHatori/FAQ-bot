"""
Test configuration file for pytest.

This file automatically sets up the Python path to allow importing
modules from the parent directory (backend) in all test files.
"""

import sys
import os
import warnings
import tempfile
import pytest
from pathlib import Path

# Suppress warnings from external libraries
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# This ensures all test files can import backend modules without
# needing to manually add sys.path modifications


@pytest.fixture(scope="function")
def temp_db():
    """Create a temporary database for testing."""
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db_file.close()

    yield temp_db_file.name

    # Cleanup
    if os.path.exists(temp_db_file.name):
        os.unlink(temp_db_file.name)


@pytest.fixture(scope="function")
def test_db_manager(temp_db):
    """Create a test database manager with initialized schema."""
    from core.database import DatabaseManager

    db_manager = DatabaseManager(temp_db)
    db_manager.initialize_schema()

    return db_manager


@pytest.fixture(scope="function")
def test_faq_manager(test_db_manager):
    """Create a test FAQ manager with initialized database."""
    from core.faq import FAQManager

    return FAQManager(test_db_manager)


@pytest.fixture(scope="function")
def test_app(test_faq_manager):
    """Create a test FastAPI app with proper dependencies."""
    from fastapi import FastAPI
    from unittest.mock import Mock
    from core.vector_store import VectorStore
    from core.claude_client import ClaudeClient
    from core.pending_changes import PendingChangesManager
    from api.dependencies import (
        get_faq_manager,
        get_vector_store,
        get_claude_client,
        get_pending_changes_manager,
    )
    from api.error_handlers import register_error_handlers
    from api.routes import faq_router, cache_router, claude_router, health_router

    app = FastAPI(
        title="FAQ Bot API",
        description="A smart FAQ bot with RAG-powered search and Claude AI integration",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create mock dependencies for testing
    mock_vector_store = Mock(spec=VectorStore)
    mock_vector_store.is_ready.return_value = True
    mock_vector_store.get_cache_info.return_value = {
        "cached": False,
        "message": "Cache not available in test environment",
    }
    mock_vector_store.search_similar_faqs.return_value = "Test context"

    mock_claude_client = Mock(spec=ClaudeClient)
    mock_claude_client.is_ready.return_value = True
    mock_claude_client.validate_credentials.return_value = (True, "")

    mock_pending_changes = Mock(spec=PendingChangesManager)
    mock_pending_changes.get_pending_changes.return_value = {
        "changes": [],
        "total_count": 0,
        "stats": {"created": 0, "updated": 0, "deleted": 0},
        "has_pending": False,
        "timestamp": "2024-01-01T00:00:00Z",
    }

    # Override dependencies
    app.dependency_overrides[get_faq_manager] = lambda: test_faq_manager
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
    app.dependency_overrides[get_claude_client] = lambda: mock_claude_client
    app.dependency_overrides[get_pending_changes_manager] = lambda: mock_pending_changes

    # Register error handlers
    register_error_handlers(app)

    # Include routers
    app.include_router(faq_router)
    app.include_router(cache_router)
    app.include_router(claude_router)
    app.include_router(health_router)

    return app


@pytest.fixture(scope="function")
def test_client(test_app):
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient

    return TestClient(test_app)
