# Atlas — Civic Accountability Orchestration Hub

## Purpose

Atlas is the central hub that connects and orchestrates queries across multiple independent civic accountability and personal data applications. It acts as the routing and integration layer — it does NOT duplicate data or logic from spoke applications.

## Architecture

Atlas uses a hub-and-spoke model. Spoke applications are independent, self-contained projects that each manage their own database and API. Atlas connects to them via their API endpoints. Spoke applications NEVER connect to or depend on each other directly.

```
                        ┌───────────┐
                        │   Atlas   │
                        │   (Hub)   │
                        └──┬─┬─┬─┬─┘
                           │ │ │ │
      ┌────────────────────┘ │ │ └────────────────────┐
      │      ┌───────────────┘ └───────────────┐      │
      ▼      ▼                                 ▼      ▼
 civic_media  article-tracker              Shasta-DB  Facebook-Offline
      │                                        │
      ├── Shasta-PRA-Backup                    ├── Shasta-Campaign-Finance
      └── Facebook-Monitor
```

## Spoke Applications

### civic_media
- **Function**: Meeting transcription, speaker diarization, voiceprint learning, summarization
- **Database**: SQLite
- **API**: FastAPI
- **Background tasks**: Celery + Redis
- **Key capabilities**: Process recordings → transcribe → diarize → summarize

### article-tracker
- **Function**: Local news aggregation and monitoring for Northern California civic journalism
- **Database**: SQLite
- **Key capabilities**: Crawl sources, store articles, search by keyword/source/date

### Shasta-DB
- **Function**: Local-first archive browser and metadata editor for civic media
- **Stack**: FastAPI / SQLAlchemy / HTMX / SQLite
- **Key capabilities**: Browse, search, tag, and annotate archived civic media

### Facebook-Offline
- **Function**: Local repository of personal Facebook archive data (messages, posts, etc.)
- **Database**: Local files / structured archive
- **Key capabilities**: Query messages and posts by keyword, date, or contact; retrieve relevant conversations for LLM analysis
- **Note**: This is a personal data archive, not a scraper. Treat all content as private.

### Shasta-PRA-Backup
- **Function**: Browse and search Shasta County public records requests scraped from NextRequest portal
- **Database**: SQLite (raw sqlite3 schema from scraper + ORM document_text table)
- **API**: FastAPI on port 8845
- **Key capabilities**: Search PRA requests, view timelines, browse documents, transcribe audio/video attachments
- **Note**: Calls civic_media's `/api/transcribe` endpoint for document transcription (only cross-spoke HTTP call outside Atlas)

### Shasta-Campaign-Finance
- **Function**: Campaign finance disclosures from NetFile Connect2 API for Shasta County
- **Database**: SQLite with async SQLAlchemy (10 ORM tables including Person, Filer, Filing, Transaction)
- **API**: FastAPI on port 8855
- **Key capabilities**: Track filers, filings, transactions, elections, people/entity resolution

### Facebook-Monitor
- **Function**: Automated monitoring and archival of public Facebook pages
- **Database**: SQLite (14 tables — posts, comments, attachments, people, entities, categories, import/media queues)
- **API**: FastAPI on port 8150
- **Key capabilities**: Scrape public pages, track comments, download media, people/entity linking, data enrichment
- **Note**: Public data monitoring tool. Uses Playwright for scraping with anti-detection measures.

## Cross-Project Rules

All projects live under E:\0-Automated-Apps\ and are loaded via --add-dir.

When working in Atlas with spoke project directories added:

1. **Read freely** — You may read any file in any spoke project to understand schemas, models, endpoints, and data structures.
2. **Write to Atlas first** — All orchestration logic, routing, and cross-app query composition lives here in Atlas.
3. **Suggest spoke changes** — If a spoke app does not expose what Atlas needs, suggest the API endpoint change and wait for approval before modifying the spoke.
4. **Modify spokes when approved** — If I explicitly approve or request a change to a spoke project, make that change.
5. **Never create spoke-to-spoke dependencies** — Spoke apps must remain independently functional. They do not import from, call, or know about each other. All cross-app communication goes through Atlas.
   **Approved exceptions** (documented peer service calls that bypass Atlas):
   - `Shasta-PRA-Backup → civic_media POST /api/transcribe` — Transcription-as-a-Service for audio/video document processing
   New cross-spoke features that require direct spoke-to-spoke calls must be approved and added to this exception list.
6. **Preserve spoke independence** — Any endpoint you add to a spoke must be generally useful, not tightly coupled to Atlas internals.
7. **Privacy** — Facebook-Offline contains personal data. Never expose its content through any public-facing endpoint. All queries to it should remain local.

## Development Workflow

When building an integration:
1. Read the target spoke's models, schemas, and existing endpoints
2. Determine if the spoke already exposes what Atlas needs
3. If yes — write the Atlas-side integration code only
4. If no — propose the new spoke endpoint, wait for approval, then implement both sides
5. Test the spoke endpoint independently before wiring it into Atlas

## Running Atlas

Start the server with:
```
python run.py
```
Do NOT use `python -m uvicorn app.main:app` directly — `run.py` sets `SO_REUSEADDR` on the socket to prevent the Windows zombie socket problem where port 8888 stays locked after a killed process.

## Tech Stack

- Python
- FastAPI or lightweight HTTP client for spoke communication
- SQLite for any Atlas-specific state (query logs, cached cross-app results)
- ChromaDB for LazyChroma RAG embedding cache (persistent but fully rebuildable)
- Ollama for local LLM inference and embeddings (nomic-embed-text)
- All spoke communication via HTTP API calls — never direct database access across apps

## Testing

No formal test suite exists yet. Use Playwright for browser-based UI testing and pytest for API/service tests.

### Setup

```bash
pip install playwright pytest pytest-asyncio httpx
python -m playwright install chromium
cd frontend && npm install  # if not already done
```

### Running Tests

```bash
pytest tests/ -v
pytest tests/ -v -k "browser"    # Playwright UI tests only
pytest tests/ -v -k "api"        # API tests only
```

### Writing Tests

- **Browser tests** go in `tests/test_browser.py` — use Playwright to verify the React frontend (chat interface, search across spokes, results rendering, spoke status indicators)
- **API tests** go in `tests/test_api.py` — use httpx against FastAPI endpoints (query routing, spoke health, tool execution)
- **Integration tests** go in `tests/test_integration.py` — verify Atlas can reach and query each spoke (requires spokes running)
- Both backend (port 8888) and frontend dev server (port 5173) must be running for browser tests
- Mock spoke responses for unit tests; use live spokes for integration tests

### Key Flows to Test

1. **Chat interface**: query submission, streaming response, source citations
2. **Cross-spoke search**: query routes to correct spokes, results aggregate
3. **Spoke health**: dashboard shows which spokes are online/offline
4. **Tool execution**: Atlas tools correctly call spoke APIs and return results
5. **RAG pipeline**: ChromaDB embedding, retrieval, and context injection

## Master Schema & Codex References

**`E:\0-Automated-Apps\MASTER_SCHEMA.md`** — Canonical cross-project database
schema and API contracts. **HARD RULE: If you add, remove, or modify any database
tables, columns, API endpoints, or response shapes, you MUST update the Master
Schema before finishing your task.** Do not skip this — other projects read it to
understand this project's data contracts.

**`E:\0-Automated-Apps\MASTER_PROJECT.md`** describes the overall ecosystem
architecture and how all projects interconnect.

> **HARD RULE — READ AND UPDATE THE CODEX**
>
> **`E:\0-Automated-Apps\master_codex.md`** is the living interoperability codex.
> 1. **READ it** at the start of any session that touches APIs, schemas, tools,
>    chunking, person models, search, or integration with other projects.
> 2. **UPDATE it** before finishing any task that changes cross-project behavior.
>    This includes: new/changed API endpoints, database schema changes, new tools
>    or tool modifications in Atlas, chunking strategy changes, person model changes,
>    new cross-spoke dependencies, or completing items from a project's outstanding work list.
> 3. **DO NOT skip this.** The codex is how projects stay in sync. If you change
>    something that another project depends on and don't update the codex, the next
>    agent working on that project will build on stale assumptions and break things.
