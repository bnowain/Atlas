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

## Master Schema Reference

**`E:\0-Automated-Apps\MASTER_SCHEMA.md`** contains the canonical cross-project
database schema. If you add, remove, or modify any database tables, fields, or
API contracts in Atlas or any spoke, **you must update the Master Schema** to keep
it in sync. The agent is authorized and encouraged to edit that file directly.

**`E:\0-Automated-Apps\MASTER_PROJECT.md`** describes the overall ecosystem
architecture and how all projects interconnect.
