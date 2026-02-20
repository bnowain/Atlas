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
       ┌────────────┘ │ │ └────────────┐
       │      ┌───────┘ └───────┐      │
       ▼      ▼                 ▼      ▼
  civic_media  article-tracker  Shasta-DB  Facebook-Offline
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

## Cross-Project Rules

All projects live under E:\0-Automated-Apps\ and are loaded via --add-dir.

When working in Atlas with spoke project directories added:

1. **Read freely** — You may read any file in any spoke project to understand schemas, models, endpoints, and data structures.
2. **Write to Atlas first** — All orchestration logic, routing, and cross-app query composition lives here in Atlas.
3. **Suggest spoke changes** — If a spoke app does not expose what Atlas needs, suggest the API endpoint change and wait for approval before modifying the spoke.
4. **Modify spokes when approved** — If I explicitly approve or request a change to a spoke project, make that change.
5. **Never create spoke-to-spoke dependencies** — Spoke apps must remain independently functional. They do not import from, call, or know about each other. All cross-app communication goes through Atlas.
6. **Preserve spoke independence** — Any endpoint you add to a spoke must be generally useful, not tightly coupled to Atlas internals.
7. **Privacy** — Facebook-Offline contains personal data. Never expose its content through any public-facing endpoint. All queries to it should remain local.

## Development Workflow

When building an integration:
1. Read the target spoke's models, schemas, and existing endpoints
2. Determine if the spoke already exposes what Atlas needs
3. If yes — write the Atlas-side integration code only
4. If no — propose the new spoke endpoint, wait for approval, then implement both sides
5. Test the spoke endpoint independently before wiring it into Atlas

## Tech Stack

- Python
- FastAPI or lightweight HTTP client for spoke communication
- SQLite for any Atlas-specific state (query logs, cached cross-app results)
- All spoke communication via HTTP API calls — never direct database access across apps
