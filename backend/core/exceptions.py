"""
Custom exception classes for the FAQ bot.
"""


class FAQBotException(Exception):
    """Base exception for FAQ bot application."""

    pass


class DatabaseError(FAQBotException):
    """Raised when database operations fail."""

    pass


class ValidationError(FAQBotException):
    """Raised when data validation fails."""

    pass


class NotFoundError(FAQBotException):
    """Raised when a requested resource is not found."""

    pass


class PermissionError(FAQBotException):
    """Raised when user lacks permission for an operation."""

    pass


class CacheError(FAQBotException):
    """Raised when cache operations fail."""

    pass


class ExternalServiceError(FAQBotException):
    """Raised when external service calls fail."""

    pass
