# Atlas — TODO

## Immediate (next session)

### Test the votes pipeline end-to-end
1. Start Atlas + civic_media
2. Run `python seed_tags.py` from civic_media root (new tags not seeded yet)
3. Run `python scripts/ingest_brown_act.py` (Brown Act PDF → DB)
4. Run `python scripts/ingest_minutes_votes.py` (votes backfill)
5. Test via chat:
   - "How did Crye vote on the CTCL grant?"
   - "All dissenting votes by Supervisor Long in 2025"
   - "What does the Brown Act say about public comment rights?"
   - "Was there a Brown Act violation in this meeting?" + meeting_id

### Summary ingest pipeline (civic_media, not Atlas)
Parse `---TAGS-*:` footer from LLM summaries → create tag_assignments records → strip footer
before storing summary text in `summary_short`/`summary_long`. Not yet built.

## Short Term

### Add instruction_manager to route queries better
The `instruction_manager` is imported in `chat_pipeline.py` but the default instruction
system isn't fully wired. Add:
- A default "civic accountability" instruction that primes the LLM on local context
  (who the supervisors are, what governing bodies exist, what the key issues are)
- Per-conversation instruction override via chat UI

### Brown Act RAG embedding
`reference_sections` rows are in civic_media DB but not yet embedded into ChromaDB.
Add `reference_sections` as a source type in Atlas `POST /api/rag/pre-index`.
Steps:
1. Add `_chunk_reference_sections()` to `rag/deterministic_chunking.py`
2. Add fetch handler in `rag/retrieval_validator.py`
3. Add `"reference_sections"` to `ALL_SOURCE_TYPES` in `rag/pre_index.py`
4. Run `POST /api/rag/pre-index` with source_type=reference_sections

### Votes in RAG pre-index
Consider whether vote records should be embedded for semantic search.
Likely approach: embed the `item_description` + outcome as a chunk,
tagged with meeting_id, governing_body, date, members.

### Instruction system (default instructions + user overrides)
Currently `instruction_manager` exists but instructions aren't serving as LLM priming.
Build:
- Default system instruction stored in DB (editable via UI)
- Per-conversation instruction override
- Civic context block: list of supervisors by district, key agencies, recurring issues

## Medium Term

### Cross-spoke timeline
Given a person name, pull their activity across all spokes sorted by date:
- civic_media: meetings they spoke at
- campaign_finance: filings/contributions by date
- article_tracker: news coverage by date
- shasta_pra: PRA requests filed/received by date

### Agenda alignment (civic_media)
Match parsed agenda items to transcript segments so votes can be linked to specific
transcript segments and timestamps.

### Summary ingest endpoint (civic_media)
`POST /api/meetings/{id}/summary/ingest` — parses `---TAGS-*:` footer, creates
tag_assignments, strips footer, stores prose only.

## Known Issues

- Multiple `python run.py` invocations create zombie processes. Kill with:
  `powershell -Command "Get-Process python* | Stop-Process -Force"`
- Shasta-DB port 8844 — verify matches actual startup port
- `shasta_db` `get_file_info` handler partially broken (falls back to search)
