# CLI Management Tools

Command-line tools for managing the Susten FAQ Bot system.

## Quick Start

```bash
# Interactive mode (recommended)
python cli/main.py

# Direct commands
python cli/main.py <tool> <command> [args...]
python cli/manage_faqs.py <command> [args...]
python cli/manage_cache.py <command> [args...]
python cli/query.py
```

## Tools

### FAQ Management (`manage_faqs.py`)
Manage FAQ database with search, CRUD operations, and analytics.

```bash
python cli/manage_faqs.py list 10 --status public
python cli/manage_faqs.py search "login"
python cli/manage_faqs.py add "Question?" "Answer" --tags login,auth
python cli/manage_faqs.py stats
```

### Cache Management (`manage_cache.py`)
Manage vector cache for search performance.

```bash
python cli/manage_cache.py status
python cli/manage_cache.py build
python cli/manage_cache.py build --force --include-private
python cli/manage_cache.py clear
```

### Interactive Query (`query.py`)
Interactive Q&A interface with the FAQ bot.

```bash
python cli/query.py
# Ask questions, use 'exit', 'quit', or 'q' to end
```

### Main CLI (`main.py`)
Unified interface for all tools with interactive menu.

```bash
python cli/main.py
# Or direct shortcuts:
python cli/main.py faq list 5
python cli/main.py cache status
```

## Configuration

### Environment Variables
```bash
export ANTHROPIC_API_KEY="your-api-key"  # Required for queries
export RAG_CACHE_DIR="custom_cache_dir"  # Optional
export FAQ_DB_PATH="path/to/faqs.db"     # Optional
```

### Default Locations
- FAQ Database: `backend/faqs.db`
- Vector Cache: `backend/rag_cache/`

## Common Workflows

### Initial Setup
1. Check database: `python cli/main.py faq stats`
2. Build cache: `python cli/main.py cache build`
3. Test system: `python cli/main.py cache test`

### Daily Operations
- Add FAQs: `python cli/manage_faqs.py add "Question" "Answer"`
- Rebuild cache: `python cli/manage_cache.py build --force`
- Query system: `python cli/query.py`

## Command Reference

### FAQ Commands
| Command | Description | Example |
|---------|-------------|---------|
| `list` | List FAQs | `list 10 --status public --tag login` |
| `search` | Search FAQs | `search "password reset"` |
| `add` | Add FAQ | `add "Q?" "A" --tags tag1,tag2` |
| `update` | Update FAQ | `update 1 --status private` |
| `delete` | Delete FAQ | `delete 1` |
| `stats` | Show stats | `stats` |
| `tags` | List tags | `tags` |
| `categories` | List categories | `categories` |

### Cache Commands
| Command | Description | Example |
|---------|-------------|---------|
| `status` | Cache status | `status` |
| `build` | Build cache | `build --include-private` |
| `clear` | Clear cache | `clear` |
| `test` | Test cache | `test` |

## Troubleshooting

**Database not found**: Ensure `faqs.db` exists in backend directory

**Cache build failed**: Check disk space and internet connection

**API not responding**: Start API server with `python app.py`

**Import errors**: Install dependencies with `uv sync`

Use `--help` with any command for detailed help. 