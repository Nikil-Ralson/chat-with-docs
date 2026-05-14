#  Chat with Docs

A **Retrieval-Augmented Generation (RAG)** application that lets you upload PDF documents and have intelligent conversations with them. Built with FastAPI, Streamlit, PostgreSQL + pgvector, Groq LLM, and sentence-transformers for local embeddings.

---

##  Features

- **Upload PDFs** — Extracts text and converts it into semantic fact-chunks automatically
- **Chat with your documents** — Ask questions and get answers grounded in your uploaded content, with source citations
- **Manage documents** — View and delete uploaded documents from the UI
- **Tag system** — Organise documents with custom tags
- **Vector similarity search** — Uses cosine distance over 384-dimensional embeddings (HNSW index) for fast, accurate retrieval
- **REST API** — Full FastAPI backend with documented endpoints
- **Docker support** — Containerised for easy deployment

---

##  Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Streamlit Frontend                   │
│  ┌─────────────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ Chat with Docs  │  │ Manage   │  │ Manage Tags │ │
│  │    (pages/)     │  │   Docs   │  │  (pages/)   │ │
│  └────────┬────────┘  └────┬─────┘  └──────┬──────┘ │
└───────────┼───────────────┼────────────────┼─────────┘
            │               │                │
            ▼               ▼                ▼
┌──────────────────────────────────────────────────────┐
│                   FastAPI Backend (api.py)            │
│   /documents/upload  /chat  /documents  /tags        │
└────────────┬────────────────────────────┬────────────┘
             │                            │
     ┌───────▼──────┐            ┌────────▼────────┐
     │  PostgreSQL  │            │  Groq LLM API   │
     │  + pgvector  │            │ (llama-3.1-8b)  │
     │  (db.py)     │            └─────────────────┘
     └──────────────┘
             │
     ┌───────▼──────────────────┐
     │  sentence-transformers   │
     │  (all-MiniLM-L6-v2)      │
     │  Local embedding model   │
     └──────────────────────────┘
```

**Data flow for a chat query:**
1. User question → embedded locally with `all-MiniLM-L6-v2`
2. Top-K most similar chunks retrieved from PostgreSQL via cosine distance
3. Retrieved chunks injected into a system prompt → sent to Groq (Llama 3.1)
4. Answer + source citations returned to the UI

---

##  Project Structure

```
chat-with-docs/
├── api.py              # FastAPI application — all REST endpoints
├── db.py               # Peewee ORM models + PostgreSQL/pgvector setup
├── llms.py             # Groq chat + sentence-transformer embeddings
├── constants.py        # System prompts for LLM calls
├── utils.py            # Shared utility helpers
├── main.py             # Streamlit app entrypoint
├── pages/
│   ├── chats_with_documents.py   # Chat UI page
│   ├── manage_documents.py       # Document upload/delete UI
│   └── manage_tags.py            # Tag management UI
├── Dockerfile
└── requirements.txt
```

---

##  Database Schema

| Table | Description |
|---|---|
| `documents` | Uploaded PDF metadata (name) |
| `tags` | User-defined tags |
| `document_tags` | Many-to-many: documents ↔ tags |
| `document_information_chunks` | Chunked text + 384-dim vector embedding per chunk |

An **HNSW index** (`vector_cosine_ops`) is created automatically on the embeddings column for fast approximate nearest-neighbour search.

---

##  Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL with the **pgvector** extension installed
- A [Groq API key](https://console.groq.com/) (free tier available)

### 1. Clone the repository

```bash
git clone https://github.com/Nikil-Ralson/chat-with-docs.git
cd chat-with-docs
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
# PostgreSQL connection
POSTGRES_DB_NAME=your_db_name
POSTGRES_DB_HOST=your_db_host
POSTGRES_DB_PORT=5432
POSTGRES_DB_USER=your_db_user
POSTGRES_DB_PASSWORD=your_db_password

# Groq LLM
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.1-8b-instant        # optional, this is the default

# Embedding model (optional, default shown)
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

> **Note:** Your PostgreSQL instance must have the `pgvector` extension available. The app will run `CREATE EXTENSION IF NOT EXISTS vector` and create all tables automatically on first startup.

## Install and Enable pgvectorscale
Install TimescaleDB with Docker:
docker pull timescale/timescaledb-ha:pg17
docker run -d --name timescaledb -p 5433:5432 -e POSTGRES_PASSWORD=asmwm5121416 timescale/timescaledb-ha:pg17
Connect to PostgreSQL using psql or TablePlus.



##  API Reference

The FastAPI server runs on port `8000` by default. Interactive docs are available at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/documents/upload` | Upload a PDF file |
| `GET` | `/documents` | List all documents with chunk counts |
| `DELETE` | `/documents/{document_id}` | Delete a document and all its chunks |
| `POST` | `/chat` | Ask a question, returns answer + sources |
| `GET` | `/tags` | List all tags |
| `POST` | `/tags` | Create a new tag |

### Example: Upload a document

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@your_document.pdf"
```

### Example: Chat with documents

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main topic of the document?", "top_k": 5}'
```

Response:
```json
{
  "answer": "The document is about ...",
  "sources": [
    { "document": "your_document.pdf", "chunk": "Relevant excerpt..." }
  ]
}
```

---

##  Tech Stack

| Component | Technology |
|---|---|
| Frontend | [Streamlit](https://streamlit.io/) 1.38 |
| Backend API | [FastAPI](https://fastapi.tiangolo.com/) 0.115 |
| Database | PostgreSQL + [pgvector](https://github.com/pgvector/pgvector) |
| ORM | [Peewee](http://docs.peewee-orm.com/) 3.17 |
| Embeddings | [sentence-transformers](https://www.sbert.net/) — `all-MiniLM-L6-v2` (local) |
| LLM | [Groq](https://groq.com/) — `llama-3.1-8b-instant` |
| PDF parsing | [PyMuPDF](https://pymupdf.readthedocs.io/) (fitz) |
| Containerisation | Docker |

---

##  Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_DB_NAME` | — | PostgreSQL database name |
| `POSTGRES_DB_HOST` | — | PostgreSQL host |
| `POSTGRES_DB_PORT` | — | PostgreSQL port |
| `POSTGRES_DB_USER` | — | PostgreSQL username |
| `POSTGRES_DB_PASSWORD` | — | PostgreSQL password |
| `GROQ_API_KEY` | — | Your Groq API key |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model to use for chat |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model for embeddings |
| `PORT` | `8000` | Port for the API server (used by Docker) |

---
