"""
Configuration management for the FAQ bot.
"""

import os
from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings with environment variable support."""

    # Database settings
    database_path: str = "faqs.db"

    # AWS/Claude settings
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    claude_model: str = "anthropic.claude-sonnet-4-20250514-v1:0"

    # RAG settings
    embedding_model: str = "intfloat/multilingual-e5-small"
    rag_cache_dir: str = "rag_cache"
    default_top_k: int = 5
    vector_distance_metric: str = "l2"  # "l2" or "cosine"

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    cors_origins: list = ["*"]

    # FAQ settings
    default_faq_status: str = "public"
    default_faq_category: str = "other"
    max_question_length: int = 500
    max_answer_length: int = 2000

    def __init__(self):
        # Load from environment variables
        super().__init__(
            database_path=os.getenv("DATABASE_PATH", "faqs.db"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            claude_model=os.getenv(
                "CLAUDE_MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0",
            ),
            embedding_model=os.getenv(
                "EMBEDDING_MODEL", "intfloat/multilingual-e5-small"
            ),
            rag_cache_dir=os.getenv("RAG_CACHE_DIR", "rag_cache"),
            default_top_k=int(os.getenv("DEFAULT_TOP_K", "5")),
            vector_distance_metric=os.getenv("VECTOR_DISTANCE_METRIC", "l2"),
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
            api_reload=os.getenv("API_RELOAD", "true").lower() == "true",
            cors_origins=(
                os.getenv("CORS_ORIGINS", "*").split(",")
                if os.getenv("CORS_ORIGINS")
                else ["*"]
            ),
            default_faq_status=os.getenv("DEFAULT_FAQ_STATUS", "public"),
            default_faq_category=os.getenv("DEFAULT_FAQ_CATEGORY", "other"),
            max_question_length=int(os.getenv("MAX_QUESTION_LENGTH", "500")),
            max_answer_length=int(os.getenv("MAX_ANSWER_LENGTH", "2000")),
        )


# Global settings instance
settings = Settings()
