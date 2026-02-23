# Last Session — 2026-02-22

## Changes Made

### Facebook-Monitor Spoke Integration (NEW)
- **app/services/tools.py** — Added 5 tool schemas: `search_monitored_posts`, `get_monitored_post`, `search_monitored_people`, `list_monitored_pages`, `get_fb_monitor_entities`. Added `FACEBOOK_MONITOR_TOOLS` list and registered in `ALL_TOOLS` and `TOOL_TO_SPOKE`.
- **app/services/tool_executor.py** — Added 5 handler functions for the Facebook-Monitor tools. Registered in `_TOOL_HANDLERS`.
- **app/services/query_classifier.py** — Added `facebook_monitor` keywords and tool mapping to `_SPOKE_TOOLS`.
- **app/services/unified_search.py** — Added `_search_fb_monitor()` searcher function and registered in `_SEARCHERS`.
- **app/services/rag/pre_index.py** — Added `"facebook_monitor"` to `ALL_SOURCE_TYPES`.
- **app/services/rag/retrieval_validator.py** — Added `facebook_monitor` fetch handler. Updated default `active_sources`.
- **app/services/rag/deterministic_chunking.py** — `_chunk_facebook_monitor()` already existed (added `"facebook_monitor"` to `_STRATEGIES`).
- **app/services/chat_pipeline.py** — Updated `SYSTEM_PROMPT` to mention Facebook-Monitor spoke.

### Campaign Finance Spoke Integration (NEW)
- **app/config.py** — Added `campaign_finance` SpokeConfig (port 8855).
- **app/services/tools.py** — Added 6 tool schemas: `search_campaign_filers`, `get_campaign_filer`, `search_campaign_transactions`, `search_campaign_filings`, `get_campaign_stats`, `search_campaign_people`. Added `CAMPAIGN_FINANCE_TOOLS` list.
- **app/services/tool_executor.py** — Added 6 handler functions for Campaign Finance tools.
- **app/services/query_classifier.py** — Added `campaign_finance` keywords and tool mapping.
- **app/services/unified_search.py** — Added `_search_campaign_finance()` searcher.
- **app/services/rag/pre_index.py** — Added `"campaign_finance"` to `ALL_SOURCE_TYPES`.
- **app/services/rag/retrieval_validator.py** — Added `campaign_finance` fetch handler.
- **app/services/rag/deterministic_chunking.py** — Added `_chunk_campaign_finance()` strategy.
- **app/services/chat_pipeline.py** — Updated `SYSTEM_PROMPT` to mention Campaign Finance spoke.

### Cross-Spoke Exception Rules
- **CLAUDE.md** — Updated rule #5 to document approved cross-spoke exceptions (PRA→civic_media transcription).

### Other
- **TODO.md** — Updated spoke test list and startup instructions.
- **CLAUDE.md** — Added Facebook-Monitor, Shasta-Campaign-Finance, and Shasta-PRA-Backup to spoke descriptions. Added Master Schema Reference section.

## What to Test
1. Start Atlas and all spokes
2. Test Facebook-Monitor tools via chat: "search Facebook Monitor posts about city council"
3. Test Campaign Finance tools via chat: "search campaign contributions for John Smith"
4. Test unified search includes all 7 spokes
5. Test RAG pre-index with `source_type=facebook_monitor` and `source_type=campaign_finance`
6. Verify health check shows all 7 spokes
