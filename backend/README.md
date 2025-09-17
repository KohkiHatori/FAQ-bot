# FAQ Bot Backend

RAG-powered FAQ system using Claude Sonnet 4, FAISS vector search, and SQLite.

## Features

- AI responses via Claude Sonnet 4 (AWS Bedrock)
- Vector search with FAISS and multilingual embeddings
- SQLite database with REST API
- Smart caching for fast startup
- Japanese and English support

## Project Structure

```
backend/
├── app.py               # FastAPI server
├── core/                # Core modules (database, vector store, FAQ manager)
├── api/                 # API routes and dependencies
├── cli/                 # Command-line tools
├── models.py            # Pydantic models
├── faqs.db              # SQLite database
├── rag_cache/           # Embeddings cache
└── tests/               # Test suite
```

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Configure AWS credentials:
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   ```

## Usage

### API Server
```bash
python app.py
```
- Server: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

### CLI Tools
```bash
python cli/main.py              # Main interface
python cli/manage_faqs.py       # FAQ management
python cli/manage_cache.py      # Cache management
python cli/query.py             # Interactive queries
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check |
| `POST` | `/query-with-rag` | AI-powered FAQ query |
| `GET` | `/faqs` | List FAQs |
| `POST` | `/faqs` | Create FAQ |
| `PUT` | `/faqs/{id}` | Update FAQ |
| `DELETE` | `/faqs/{id}` | Delete FAQ |
| `GET` | `/cache` | Cache status |
| `POST` | `/cache/rebuild` | Rebuild cache |

### Example Usage

```bash
# AI query
curl -X POST "http://localhost:8000/query-with-rag" \
  -H "Content-Type: application/json" \
  -d '{"message": "積立額はいくらからですか？"}'

# List FAQs
curl "http://localhost:8000/faqs?limit=10&status=public"
```

## Architecture

```
User Query → Vector Search → Context Retrieval → Claude → Response
```

**Components:**
- FAISS vector search with multilingual embeddings
- AWS Bedrock integration with streaming responses
- SQLite database with full-text search
- Automatic embeddings caching

## Performance

- **Database**: SQLite with 130+ FAQ entries
- **Embedding Model**: `intfloat/multilingual-e5-small`
- **First run**: ~30-60 seconds (building cache)
- **Cached runs**: ~2-5 seconds

## Deployment

### Development
```bash
python app.py
```

### Production
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## Code Formatting

Uses [Black](https://black.readthedocs.io/) for code formatting.

```bash
# Format code
black backend/

# Check formatting
black --check backend/

# Setup pre-commit hook
./scripts/setup-git-hooks.sh
```

Configuration in `pyproject.toml`:
```toml
[tool.black]
line-length = 88
target-version = ['py39']
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_faq_manager.py

# Run with coverage
pytest --cov=core --cov=api
```

## Requirements

- Python 3.11+
- AWS Bedrock access (Claude Sonnet 4)
- ~500MB disk space for embeddings cache 