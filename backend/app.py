"""
Refactored FastAPI application for the FAQ bot with clean architecture.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Core imports
from core.database import db_manager
from core.config import settings

# API imports
from api.error_handlers import register_error_handlers
from api.dependencies import get_vector_store, get_claude_client, get_faq_manager
from api.routes import faq_router, cache_router, claude_router, health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    print("🚀 Starting FAQ Bot API...")

    # Initialize database schema
    print("🔧 Initializing database...")
    db_manager.initialize_schema()
    print("✅ Database initialized")

    # Initialize RAG system
    print("📚 Initializing RAG system...")
    vector_store = get_vector_store()
    faq_manager = get_faq_manager()
    rag_initialized = vector_store.initialize(faq_manager)

    if rag_initialized:
        print("✅ RAG system ready")
    else:
        print("⚠️  RAG system failed to initialize - some features may be unavailable")

    # Initialize Claude client
    print("🤖 Initializing Claude AI...")
    claude_client = get_claude_client()
    claude_initialized = claude_client.initialize()

    if claude_initialized:
        print("✅ Claude AI ready")
    else:
        print("⚠️  Claude AI failed to initialize - AI features may be unavailable")

    print("🎉 FAQ Bot API is ready!")

    yield

    print("🛑 Shutting down FAQ Bot API...")


# Create FastAPI application
app = FastAPI(
    title="FAQ Bot API",
    description="A smart FAQ bot with RAG-powered search and Claude AI integration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register error handlers
register_error_handlers(app)

# Include routers
app.include_router(health_router)
app.include_router(faq_router)
app.include_router(cache_router)
app.include_router(claude_router)


if __name__ == "__main__":
    import uvicorn

    print("Starting FAQ Bot API server...")
    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
