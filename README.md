# Susten FAQ Bot

RAG-powered FAQ system with FastAPI backend and Next.js frontend.

## Project Structure

```
susten-faq-bot/
├── backend/                # Python backend (FastAPI, SQLite, RAG)
├── frontend/               # Next.js frontend
├── pyproject.toml          # Python dependencies
└── scripts/                # Setup scripts
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Setup
1. Install dependencies:
   ```bash
   uv sync
   cd frontend && npm install
   ```

2. Sync FAQ data (first time only):
   ```bash
   uv run python backend/cli/manage_faqs.py sync <csv_file>
   ```

3. Configure AWS credentials:
   ```bash
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   ```

### Run Application

**Backend:**
```bash
cd backend && python app.py
```

**Frontend:**
```bash
cd frontend && npm run dev
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`

## Features

- AI-powered responses via Claude Sonnet 4 (AWS Bedrock)
- Vector search with FAISS and semantic embeddings
- SQLite database with full-text search
- Real-time streaming chat interface
- FAQ management with CRUD operations
- Smart caching for fast performance
- Japanese and English support

## Development

### Backend Commands
```bash
cd backend
python app.py                        # Start server
python cli/main.py                   # CLI interface
python cli/manage_faqs.py            # FAQ management
python cli/manage_cache.py           # Cache management
pytest                               # Run tests
black backend/                       # Format code
```

### Frontend Commands
```bash
cd frontend
npm run dev                          # Development server
npm run build                        # Build for production
npm run lint                         # Lint code
```

### Code Formatting
```bash
# Setup git hooks for auto-formatting
./scripts/setup-git-hooks.sh

# Manual formatting
black backend/
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check |
| `POST` | `/query-with-rag` | AI-powered FAQ query |
| `GET` | `/faqs` | List FAQs |
| `POST` | `/faqs` | Create FAQ |
| `GET` | `/cache` | Cache status |
| `POST` | `/cache/rebuild` | Rebuild cache |

## Configuration

Environment variables:
```bash
AWS_ACCESS_KEY_ID="your-access-key"
AWS_SECRET_ACCESS_KEY="your-secret-key"
AWS_REGION="ap-northeast-1"  # Optional, default
```

## Architecture

```
Frontend (Next.js) ↔ Backend (FastAPI) ↔ Vector Store (FAISS) ↔ Claude AI
                                      ↕
                                SQLite Database
```

For detailed documentation, see:
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
- [CLI README](backend/cli/README.md) 