# Backend Test Suite

This directory contains a comprehensive test suite for the SUSTEN FAQ Bot backend. The tests are designed to run without external dependencies using proper mocking.

## 📁 Structure

```
tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Test configuration and fixtures
├── pytest.ini                 # Pytest configuration
├── README.md                   # This file
├── test_app.py                 # FastAPI application integration tests
├── test_cache_routes.py        # Cache API endpoint tests
├── test_claude_client.py       # Claude AI client tests
├── test_claude_routes.py       # Claude API endpoint tests
├── test_database.py            # Database functionality tests
├── test_faq_manager.py         # FAQ business logic tests
├── test_faq_routes.py          # FAQ API endpoint tests
├── test_health_routes.py       # Health check endpoint tests
├── test_pending_changes.py     # Pending changes functionality tests
└── test_vector_store.py        # Vector search functionality tests
```

## 🚀 Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_app.py

# Run tests in parallel
pytest -n auto

# Verbose output
pytest -vv
```

## 📋 Test Organization

### Core Business Logic
- **`test_database.py`** - Database operations and connection management
- **`test_faq_manager.py`** - FAQ CRUD operations and business logic
- **`test_pending_changes.py`** - Pending changes tracking and management
- **`test_vector_store.py`** - Vector search and cache operations
- **`test_claude_client.py`** - Claude AI integration and query processing

### API Endpoints
- **`test_app.py`** - FastAPI application integration tests
- **`test_faq_routes.py`** - FAQ API endpoints (`/api/faqs/`)
- **`test_cache_routes.py`** - Cache API endpoints (`/cache`)
- **`test_claude_routes.py`** - Claude query endpoints (`/api/claude/`)
- **`test_health_routes.py`** - Health check endpoints (`/health`)

## 🔧 Common Commands

```bash
# Basic usage
pytest                                    # Run all tests
pytest tests/test_faq_routes.py          # Run specific file
pytest -k "test_cache"                   # Run tests matching pattern
pytest -x                                # Stop on first failure

# Coverage and reporting
pytest --cov=. --cov-report=html        # Generate HTML coverage report
pytest -v                               # Verbose output
pytest -n auto                          # Run in parallel

# Debugging
pytest --pdb                            # Drop into debugger on failures
pytest -s                               # Don't capture output
```

## 📊 Test Coverage

### Core Components
- **Database Operations** - Connection management, queries, transactions
- **FAQ Management** - CRUD operations, search, validation
- **Pending Changes** - Change tracking, persistence, statistics
- **Vector Search** - Embeddings, similarity search, cache management
- **Claude Integration** - AI queries, context handling, error management

### API Endpoints
- **FAQ Routes** - Create, read, update, delete FAQs
- **Cache Routes** - Cache info and rebuild operations
- **Claude Routes** - AI query processing with context
- **Health Routes** - System health monitoring
- **Error Handling** - Validation, exceptions, HTTP errors

## 🎭 Mocking Strategy

All external dependencies are mocked for fast, reliable testing:

- **AWS Services** - Mock Claude AI client and responses
- **Database Operations** - Use in-memory SQLite for fast testing
- **Vector Operations** - Mock embedding generation and similarity search
- **API Testing** - Use FastAPI's `TestClient` with mocked dependencies

## 🚨 Troubleshooting

### Common Issues
1. **Import Errors** - Ensure you're running from the `backend/` directory
2. **Database Errors** - Tests use temporary databases that are cleaned up automatically
3. **Mock Issues** - Verify mock patch paths match actual import paths

### Debug Commands
```bash
pytest --pdb                            # Drop into debugger on failures
pytest -s                               # Show print statements
pytest --tb=long                        # Detailed tracebacks
```

## ⚡ Performance

The test suite is optimized for speed:
- Comprehensive mocking eliminates slow external calls
- In-memory databases for fast database tests
- Parallel execution support

**Typical run times:**
- Individual test files: 1-3 seconds
- Full test suite: 10-15 seconds
- With coverage: 15-20 seconds

## ✅ Key Features

- **Zero External Dependencies** - All external services are mocked
- **Fast Execution** - Optimized for developer productivity
- **Comprehensive Coverage** - Tests all critical functionality
- **CI/CD Ready** - Reliable in automated environments
- **Easy Debugging** - Clear output and debugging options 