# Backend Specification - SUSTEN FAQ Bot

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Data Models](#data-models)
5. [API Endpoints](#api-endpoints)
6. [Database Schema](#database-schema)
7. [Configuration](#configuration)
8. [Error Handling](#error-handling)
9. [Dependencies](#dependencies)
10. [Implementation Details](#implementation-details)

## System Overview

The SUSTEN FAQ Bot backend is a FastAPI-based application that provides:
- **FAQ Management**: CRUD operations for frequently asked questions
- **RAG (Retrieval-Augmented Generation)**: Vector-based semantic search with FAISS
- **AI Integration**: Claude AI via AWS Bedrock for intelligent responses
- **Streaming Responses**: Real-time AI response streaming
- **Cache Management**: Vector embedding cache with automatic rebuilding
- **Pending Changes**: Status tracking for FAQ modifications requiring re-embedding

### Key Features
- Multi-language support (Japanese/English)
- Real-time vector search with semantic similarity
- Automatic FAQ status management for vector cache consistency
- Streaming AI responses with conversation history
- Full-text search with SQLite FTS5
- Comprehensive error handling and validation

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                API LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI App                                                                │
│  ├── FAQ Routes (/faqs, /faqs/{id}, /faqs/tags, etc.)                       │
│  ├── Claude Routes (/query-with-rag)                                        │
│  ├── Cache Routes (/cache, /cache/rebuild)                                  │
│  └── Health Routes (/, /health)                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE SERVICES                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   FAQ Manager   │  │  Vector Store   │  │  Claude Client  │              │
│  │                 │  │                 │  │                 │              │
│  │ • CRUD Ops      │  │ • FAISS Index   │  │ • AWS Bedrock   │              │
│  │ • Validation    │  │ • Embeddings    │  │ • Streaming     │              │
│  │ • Status Mgmt   │  │ • Similarity    │  │ • Prompts       │              │
│  │ • Search        │  │ • Cache Mgmt    │  │ • Validation    │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│           │                     │                     │                     │
│  ┌─────────────────┐  ┌─────────────────┐                                   │
│  │ Database Mgr    │  │ Pending Changes │                                   │
│  │                 │  │ Manager         │                                   │
│  │ • Connections   │  │                 │                                   │
│  │ • Transactions  │  │ • Change Track  │                                   │
│  │ • Schema Init   │  │ • JSON Store    │                                   │
│  └─────────────────┘  └─────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               DATA LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ SQLite Database │  │ Vector Cache    │  │ Pending Changes │              │
│  │                 │  │                 │  │                 │              │
│  │ • faqs table    │  │ • index.faiss   │  │ • pending_      │              │
│  │ • faqs_fts      │  │ • documents.pkl │  │   changes.json  │              │
│  │ • indexes       │  │ • metadata.json │  │                 │              │
│  │ • triggers      │  │                 │  │                 │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVICES                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                                   │
│  │ AWS Bedrock     │  │ HuggingFace     │                                   │
│  │                 │  │                 │                                   │
│  │ • Claude Sonnet │  │ • Sentence      │                                   │
│  │ • Streaming API │  │   Transformers  │                                   │
│  │ • Authentication│  │ • Multilingual  │                                   │
│  └─────────────────┘  └─────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Dependencies
- **API Layer**: Handles HTTP requests, validation, and response formatting
- **Core Services**: Business logic and data processing
- **Data Layer**: Persistent storage and caching
- **External Services**: Third-party AI and ML services

## Core Components

### 1. FAQ Manager (`core/faq.py`)
**Purpose**: Central business logic for FAQ operations with integrated data access

**Key Responsibilities**:
- FAQ CRUD operations with validation
- Status management for vector cache consistency
- Full-text search integration
- Tag and category management
- Statistics and analytics
- Pending changes coordination

**Key Methods**:
```python
# Public API
get_faq_by_id(faq_id: int) -> FAQResponse
get_faqs(limit: int, offset: int, status: str, category: str, tag: str) -> Dict
create_faq(request: FAQCreateRequest) -> FAQResponse
update_faq(faq_id: int, request: FAQUpdateRequest) -> Tuple[FAQResponse, FAQResponse]
delete_faq(faq_id: int) -> FAQResponse
search_faqs(query: str, limit: int) -> List[FAQResponse]
load_faqs_for_rag() -> List[Dict]
restore_faq_statuses_after_rebuild() -> Dict

# Internal data access
_get_by_id(faq_id: int) -> Optional[FAQResponse]
_create(question: str, answer: str, status: str, category: str, tags: List[str]) -> FAQResponse
_update(faq_id: int, **updates) -> Optional[FAQResponse]
_delete(faq_id: int) -> Optional[FAQResponse]
_search(query_text: str, limit: int) -> List[FAQResponse]
```

**Status Management Flow**:
1. New/Updated FAQs → Set to "pending" status
2. Track original intended status in pending changes
3. Cache rebuild → Process all pending FAQs
4. Restore original statuses after successful embedding

### 2. Vector Store (`core/vector_store.py`)
**Purpose**: Manages vector embeddings and semantic search using FAISS

**Key Responsibilities**:
- Sentence transformer model management
- Vector embedding generation
- FAISS index creation and management
- Semantic similarity search
- Cache persistence and loading
- Dual-query search strategy for Japanese content

**Architecture**:
```
FAQ Text Processing Pipeline:

FAQ Text Input
      │
      ▼
┌─────────────────┐
│ Sentence        │  ← Uses multilingual-e5-small model
│ Transformer     │    for Japanese/English support
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Vector          │  ← 384-dimensional embeddings
│ Embeddings      │    with L2 or cosine distance
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ FAISS Index     │  ← In-memory index for fast search
│                 │    IndexFlatL2 or IndexFlatIP
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Similarity      │  ← Dual-query strategy for
│ Search          │    better Japanese results
└─────────────────┘

Cache File Structure:
rag_cache/
├── index.faiss           # FAISS vector index
├── documents.pkl         # Serialized FAQ documents  
├── metadata.json         # Cache metadata and stats
└── pending_changes.json  # Pending changes tracking
```

**Key Methods**:
```python
initialize(faq_manager) -> bool
search_similar_faqs(query: str, top_k: int) -> str
rebuild_cache(faq_manager) -> Dict
get_cache_info() -> Dict
is_ready() -> bool
```

**Search Strategy**:
- **Dual Query Approach**: Uses both Japanese-specific and general query formats
- **Distance Metrics**: Supports both L2 and cosine similarity
- **Text Formatting**: Uses "passage:" prefix for FAQ content, "query:" for searches

### 3. Claude Client (`core/claude_client.py`)
**Purpose**: AWS Bedrock integration for Claude AI responses

**Key Responsibilities**:
- AWS Bedrock client management
- Streaming response generation
- Conversation history processing
- System prompt construction
- Credential validation

**Key Methods**:
```python
initialize() -> bool
ask_with_context_stream(message: str, retrieved_context: str, top_k: int, conversation_history: str) -> AsyncGenerator[str, None]
validate_credentials() -> Tuple[bool, str]
create_system_prompt(message: str, conversation_context: str, retrieved_context: str) -> str
build_conversation_context(conversation_history: List[Message], max_messages: int) -> str
```

**Streaming Response Format**:
```json
{
  "type": "content|error",
  "text": "response_text",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 4. Database Manager (`core/database.py`)
**Purpose**: SQLite database connection and transaction management

**Key Responsibilities**:
- Connection pooling with thread-local storage
- Transaction management with automatic rollback
- Schema initialization and migration
- Query execution with proper error handling

**Key Methods**:
```python
get_connection() -> Generator[sqlite3.Connection, None, None]
get_transaction() -> Generator[sqlite3.Connection, None, None]
execute_query(query: str, params: tuple) -> list
execute_one(query: str, params: tuple) -> Optional[sqlite3.Row]
execute_update(query: str, params: tuple) -> int
execute_insert(query: str, params: tuple) -> int
initialize_schema()
```

### 5. Pending Changes Manager (`core/pending_changes.py`)
**Purpose**: Tracks FAQ modifications requiring vector re-embedding

**Key Responsibilities**:
- Change tracking (CREATE, UPDATE, DELETE operations)
- Original status preservation
- Batch processing for cache rebuilds
- JSON file persistence

**Change Types**:
```python
class ChangeType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
```

**Key Methods**:
```python
add_pending_change(faq_id: int, change_type: ChangeType, original_status: str)
get_pending_changes() -> Dict
clear_all_pending_changes() -> Dict
get_changes_for_rebuild() -> List[PendingChange]
```

## Data Models

### Request Models
```python
class QueryRequest(BaseModel):
    message: str
    conversationHistory: str = ""
    top_k: int = 3

class FAQCreateRequest(BaseModel):
    question: str
    answer: str
    status: str = "public"  # "public", "private", "pending"
    category: str = "other"
    tags: List[str] = []

class FAQUpdateRequest(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
```

### Response Models
```python
class FAQResponse(BaseModel):
    id: int
    question: str
    answer: str
    status: str = "public"
    category: str = "other"
    tags: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class FAQListResponse(BaseModel):
    faqs: List[FAQResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

class CacheInfoResponse(BaseModel):
    cached: bool
    cache_dir: Optional[str] = None
    metadata: Optional[dict] = None
    file_sizes: Optional[dict] = None
    error: Optional[str] = None

class PendingChangesResponse(BaseModel):
    changes: List[PendingChangeResponse]
    total_count: int
    stats: dict
    has_pending: bool
    timestamp: str
```

## API Endpoints

### FAQ Management
```
GET    /faqs                 - List FAQs with pagination and filtering
POST   /faqs                 - Create new FAQ
PUT    /faqs/{id}            - Update FAQ
DELETE /faqs/{id}            - Delete FAQ
GET    /faqs/tags            - Get all unique tags
GET    /faqs/categories      - Get all categories
GET    /faqs/pending         - Get pending changes
```

### AI Query
```
POST   /query-with-rag       - AI-powered responses with RAG context (streaming)
```

### Cache Management
```
GET    /cache                - Get cache information
POST   /cache/rebuild        - Rebuild vector cache
```

### Health & Status
```
GET    /                     - Root endpoint with system info
GET    /health               - Health check
```

### Detailed Endpoint Specifications

#### GET /faqs
**Purpose**: Retrieve FAQs with pagination and filtering

**Query Parameters**:
- `limit`: int (1-500, default: 50) - Number of FAQs to return
- `offset`: int (≥0, default: 0) - Number of FAQs to skip
- `status`: string (optional) - Filter by status ("public", "private", "pending")
- `category`: string (optional) - Filter by category
- `tag`: string (optional) - Filter by tag

**Response**: `FAQListResponse`

#### POST /faqs
**Purpose**: Create a new FAQ

**Request Body**: `FAQCreateRequest`
**Response**: `FAQCreateResponse`

**Business Logic**:
1. Validate input (question/answer length, status values, tags)
2. Set status to "pending" (regardless of requested status)
3. Store original intended status in pending changes
4. Return created FAQ with pending status

#### POST /query-with-rag
**Purpose**: Generate AI responses using RAG context

**Request Body**: `QueryRequest`
**Response**: Server-Sent Events (text/event-stream)

**Processing Flow**:
1. Validate query and system readiness
2. Retrieve similar FAQs using vector search
3. Build conversation context from history
4. Create system prompt with RAG context
5. Stream Claude AI response

**Stream Format**:
```
data: {"type": "content", "text": "response_chunk", "timestamp": "..."}

data: {"type": "error", "text": "error_message", "timestamp": "..."}
```

#### POST /cache/rebuild
**Purpose**: Rebuild vector cache with current FAQ data

**Response**: `CacheActionResponse`

**Processing Flow**:
1. Clear existing cache files
2. Load all FAQs from database
3. Generate embeddings for all FAQ texts
4. Build FAISS index
5. Save cache to disk
6. Restore original FAQ statuses from pending changes
7. Clear pending changes

## Database Schema

### FAQs Table
```sql
CREATE TABLE faqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    status TEXT DEFAULT 'public',
    category TEXT DEFAULT 'other',
    tags TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_question ON faqs(question);
CREATE INDEX idx_answer ON faqs(answer);
CREATE INDEX idx_status ON faqs(status);
CREATE INDEX idx_category ON faqs(category);
```

### Full-Text Search (FTS5)
```sql
CREATE VIRTUAL TABLE faqs_fts USING fts5(
    question, answer, content='faqs', content_rowid='id'
);

-- Triggers for automatic FTS updates
CREATE TRIGGER faqs_ai AFTER INSERT ON faqs BEGIN
    INSERT INTO faqs_fts(rowid, question, answer)
    VALUES (new.id, new.question, new.answer);
END;

CREATE TRIGGER faqs_ad AFTER DELETE ON faqs BEGIN
    INSERT INTO faqs_fts(faqs_fts, rowid, question, answer)
    VALUES('delete', old.id, old.question, old.answer);
END;

CREATE TRIGGER faqs_au AFTER UPDATE ON faqs BEGIN
    INSERT INTO faqs_fts(faqs_fts, rowid, question, answer)
    VALUES('delete', old.id, old.question, old.answer);
    INSERT INTO faqs_fts(rowid, question, answer)
    VALUES (new.id, new.question, new.answer);
END;
```

## Configuration

### Environment Variables
```python
# Database
DATABASE_PATH="faqs.db"

# AWS/Claude
AWS_ACCESS_KEY_ID="your_access_key"
AWS_SECRET_ACCESS_KEY="your_secret_key"
AWS_REGION="ap-northeast-1"
CLAUDE_MODEL="apac.anthropic.claude-sonnet-4-20250514-v1:0"

# RAG
EMBEDDING_MODEL="intfloat/multilingual-e5-small"
RAG_CACHE_DIR="rag_cache"
DEFAULT_TOP_K="5"
VECTOR_DISTANCE_METRIC="l2"

# API
API_HOST="0.0.0.0"
API_PORT="8000"
API_RELOAD="true"
CORS_ORIGINS="*"

# FAQ Validation
MAX_QUESTION_LENGTH="500"
MAX_ANSWER_LENGTH="2000"
DEFAULT_FAQ_STATUS="public"
DEFAULT_FAQ_CATEGORY="other"
```

### Settings Class
```python
class Settings(BaseModel):
    # All environment variables are loaded in __init__
    # with proper type conversion and defaults
```

## Error Handling

### Exception Hierarchy
```python
FAQBotException (Base)
├── DatabaseError
├── ValidationError
├── NotFoundError
├── PermissionError
├── CacheError
└── ExternalServiceError
```

### HTTP Status Mapping
- `ValidationError` → 400 Bad Request
- `NotFoundError` → 404 Not Found
- `PermissionError` → 403 Forbidden
- `DatabaseError` → 500 Internal Server Error
- `CacheError` → 503 Service Unavailable
- `ExternalServiceError` → 502 Bad Gateway

### Error Response Format
```json
{
  "error": "Error Type",
  "message": "Human-readable error message",
  "type": "error_type_identifier"
}
```

## Dependencies

### Dependency Injection System
```python
@lru_cache()
def get_faq_manager() -> FAQManager
@lru_cache()
def get_vector_store() -> VectorStore
@lru_cache()
def get_claude_client() -> ClaudeClient
@lru_cache()
def get_pending_changes_manager() -> PendingChangesManager
```

**Benefits**:
- Singleton pattern for expensive resources
- Easy testing with dependency overrides
- Clean separation of concerns

### External Dependencies
```python
# Core Framework
fastapi==0.104.1
uvicorn==0.24.0

# Database
sqlite3 (built-in)

# AI/ML
sentence-transformers==2.2.2
faiss-cpu==1.7.4
boto3==1.34.0

# Utilities
pydantic==2.5.0
numpy==1.24.3
```

## Implementation Details

### Application Lifecycle
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting FAQ Bot API...")
    db_manager.initialize_schema()
    vector_store.initialize(faq_manager)
    claude_client.initialize()
    print("🎉 FAQ Bot API is ready!")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down FAQ Bot API...")
```

### Vector Cache Structure
```
rag_cache/
├── index.faiss           # FAISS vector index
├── documents.pkl         # Serialized FAQ documents
├── metadata.json         # Cache metadata and stats
└── pending_changes.json  # Pending changes tracking
```

### Metadata Format
```json
{
  "model_name": "intfloat/multilingual-e5-small",
  "document_count": 134,
  "embedding_dimension": 384,
  "distance_metric": "l2",
  "created_at": "2024-01-01T00:00:00Z",
  "cache_dir": "rag_cache"
}
```

### FAQ Status Workflow
```
FAQ Status State Machine:

    [New FAQ Created]
           │
           ▼
    ┌─────────────┐
    │   PENDING   │ ← All new/updated FAQs start here
    └─────────────┘
           │
           ▼ (Cache Rebuild)
    ┌─────────────┐
    │   PUBLIC    │ ← Restored from pending changes
    └─────────────┘
           │
           ▼ (FAQ Updated)
    ┌─────────────┐
    │   PENDING   │ ← Back to pending for re-embedding
    └─────────────┘

Alternative paths:
    PENDING → PRIVATE (if original status was private)
    PUBLIC/PRIVATE → [DELETED] (if FAQ deleted)

Status Management Rules:
1. Create/Update → Always set to PENDING initially
2. Store original intended status in pending_changes.json
3. Cache rebuild → Process all PENDING FAQs
4. Success → Restore original statuses from pending changes
5. Failure → FAQs remain PENDING until next successful rebuild
```

### Search Implementation Details

#### Full-Text Search (FTS5)
- Uses SQLite's FTS5 for fast text search
- Searches both question and answer fields
- Returns ranked results by relevance

#### Vector Search (FAISS)
- Dual-query strategy for better Japanese results
- Supports both L2 and cosine distance metrics
- Configurable top-k results

#### Combined Search Strategy
```python
# For user queries, use vector search for semantic similarity
# For admin searches, use FTS5 for exact text matching
```

### Performance Considerations

#### Caching Strategy
- Vector embeddings cached to disk
- FAQ manager uses database connection pooling
- Dependency injection with singleton pattern

#### Memory Management
- FAISS index loaded in memory for fast search
- Sentence transformer model cached after first use
- Database connections properly closed

#### Scalability Notes
- SQLite suitable for moderate FAQ volumes (<10K)
- FAISS index scales well with document count
- Consider PostgreSQL for larger deployments

### Security Considerations

#### Input Validation
- All user inputs validated through Pydantic models
- SQL injection prevention through parameterized queries
- File path validation for cache operations

#### AWS Credentials
- Credentials loaded from environment variables
- No hardcoded secrets in codebase
- Proper error handling for missing credentials

#### CORS Configuration
- Configurable allowed origins
- Default allows all origins for development
- Should be restricted in production

This specification provides a complete blueprint for recreating the SUSTEN FAQ Bot backend, including all architectural decisions, implementation details, and operational considerations. 