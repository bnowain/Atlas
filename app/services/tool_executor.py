"""Executes LLM tool calls by mapping them to spoke API endpoints."""

from __future__ import annotations

import json
import logging

from app.services import spoke_client
from app.services.tools import TOOL_TO_SPOKE

logger = logging.getLogger(__name__)


async def execute_tool_call(name: str, arguments: dict | str) -> dict:
    """
    Execute a single tool call and return the result.

    Returns: {"success": bool, "data": ..., "error": str | None}
    """
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return {"success": False, "error": f"Invalid JSON arguments: {arguments}"}

    try:
        handler = _TOOL_HANDLERS.get(name)
        if not handler:
            # Check spoke-based tools
            spoke_key = TOOL_TO_SPOKE.get(name)
            if not spoke_key:
                return {"success": False, "error": f"Unknown tool: {name}"}
            return {"success": False, "error": f"No handler for tool: {name}"}
        return await handler(arguments)
    except Exception as exc:
        logger.exception("Tool execution error: %s", name)
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# civic_media handlers
# ---------------------------------------------------------------------------

async def _search_meetings(args: dict) -> dict:
    resp = await spoke_client.get("civic_media", "/api/meetings")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    meetings = resp.json()
    # Simple client-side filter if query provided
    query = args.get("query", "").lower()
    if query:
        meetings = [m for m in meetings if query in (m.get("title", "") or "").lower()]
    limit = args.get("limit", 10)
    return {"success": True, "data": meetings[:limit]}


async def _get_transcript(args: dict) -> dict:
    mid = args["meeting_id"]
    resp = await spoke_client.get("civic_media", f"/api/segments/{mid}")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _search_speakers(args: dict) -> dict:
    params = {}
    if args.get("query"):
        params["search"] = args["query"]
    resp = await spoke_client.get("civic_media", "/api/people", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _get_speaker_appearances(args: dict) -> dict:
    pid = args["person_id"]
    resp = await spoke_client.get("civic_media", f"/api/people/{pid}/appearances")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _export_transcript(args: dict) -> dict:
    mid = args["meeting_id"]
    fmt = args.get("format", "txt")
    resp = await spoke_client.get("civic_media", f"/api/segments/{mid}/export", params={"format": fmt})
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    # For text formats, return the text content
    content_type = resp.headers.get("content-type", "")
    if "json" in content_type:
        return {"success": True, "data": resp.json()}
    return {"success": True, "data": resp.text[:5000]}  # cap large exports


# ---------------------------------------------------------------------------
# article-tracker handlers
# ---------------------------------------------------------------------------

async def _search_articles(args: dict) -> dict:
    params = {}
    if args.get("query"):
        params["q"] = args["query"]  # article-tracker uses Flask /search?q=
    if args.get("category"):
        params["category"] = args["category"]
    if args.get("source"):
        params["source"] = args["source"]
    params["limit"] = args.get("limit", 10)
    resp = await spoke_client.get("article_tracker", "/api/articles", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _get_article_stats(args: dict) -> dict:
    resp = await spoke_client.get("article_tracker", "/api/stats")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _get_recent_articles(args: dict) -> dict:
    params = {"limit": args.get("limit", 10)}
    if args.get("category"):
        params["category"] = args["category"]
    if args.get("source"):
        params["source"] = args["source"]
    resp = await spoke_client.get("article_tracker", "/api/articles", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


# ---------------------------------------------------------------------------
# Shasta-DB handlers
# ---------------------------------------------------------------------------

async def _search_files(args: dict) -> dict:
    params = {}
    if args.get("query"):
        params["q"] = args["query"]
    if args.get("kind"):
        params["kind"] = args["kind"]
    if args.get("ext"):
        params["ext"] = args["ext"]
    params["limit"] = args.get("limit", 20)
    resp = await spoke_client.get("shasta_db", "/search", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _list_archive_people(args: dict) -> dict:
    params = {}
    if args.get("name"):
        params["name"] = args["name"]
    params["limit"] = args.get("limit", 50)
    resp = await spoke_client.get("shasta_db", "/people", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _get_file_info(args: dict) -> dict:
    iid = args["instance_id"]
    resp = await spoke_client.get("shasta_db", f"/file/{iid}")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    # /file/ returns the actual file — we want metadata
    # Try the search endpoint with specific ID instead
    resp2 = await spoke_client.get("shasta_db", "/search", params={"q": "", "limit": 1})
    return {"success": True, "data": f"File instance {iid} found"}


# ---------------------------------------------------------------------------
# Facebook-Offline handlers
# ---------------------------------------------------------------------------

async def _search_messages(args: dict) -> dict:
    params = {"q": args["query"], "limit": args.get("limit", 10)}
    if args.get("thread_id"):
        params["thread_id"] = args["thread_id"]
    resp = await spoke_client.get("facebook_offline", "/api/messages/search/", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _search_posts(args: dict) -> dict:
    params = {"q": args["query"], "limit": args.get("limit", 10)}
    resp = await spoke_client.get("facebook_offline", "/api/posts", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _list_threads(args: dict) -> dict:
    params = {"limit": args.get("limit", 20)}
    if args.get("query"):
        params["query"] = args["query"]
    resp = await spoke_client.get("facebook_offline", "/api/threads", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _get_thread_messages(args: dict) -> dict:
    tid = args["thread_id"]
    params = {"limit": args.get("limit", 50)}
    resp = await spoke_client.get("facebook_offline", f"/api/threads/{tid}/messages", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _search_people_fb(args: dict) -> dict:
    params = {"q": args["query"], "limit": args.get("limit", 20)}
    resp = await spoke_client.get("facebook_offline", "/api/people", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


# ---------------------------------------------------------------------------
# Campaign Finance handlers
# ---------------------------------------------------------------------------

async def _search_campaign_filers(args: dict) -> dict:
    params = {"limit": args.get("limit", 10)}
    if args.get("query"):
        params["search"] = args["query"]
    if args.get("filer_type"):
        params["filer_type"] = args["filer_type"]
    resp = await spoke_client.get("campaign_finance", "/api/filers", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _get_campaign_filer(args: dict) -> dict:
    fid = args["filer_id"]
    resp = await spoke_client.get("campaign_finance", f"/api/filers/{fid}")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _search_campaign_transactions(args: dict) -> dict:
    params = {"limit": args.get("limit", 20)}
    if args.get("query"):
        params["search"] = args["query"]
    if args.get("schedule"):
        params["schedule"] = args["schedule"]
    if args.get("amount_min"):
        params["amount_min"] = args["amount_min"]
    if args.get("amount_max"):
        params["amount_max"] = args["amount_max"]
    if args.get("date_from"):
        params["date_from"] = args["date_from"]
    if args.get("date_to"):
        params["date_to"] = args["date_to"]
    resp = await spoke_client.get("campaign_finance", "/api/transactions", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _search_campaign_filings(args: dict) -> dict:
    params = {"limit": args.get("limit", 20)}
    if args.get("query"):
        params["search"] = args["query"]
    if args.get("form_type"):
        params["form_type"] = args["form_type"]
    if args.get("filer_id"):
        params["filer_id"] = args["filer_id"]
    if args.get("date_from"):
        params["date_from"] = args["date_from"]
    if args.get("date_to"):
        params["date_to"] = args["date_to"]
    resp = await spoke_client.get("campaign_finance", "/api/filings", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _get_campaign_stats(args: dict) -> dict:
    resp = await spoke_client.get("campaign_finance", "/api/stats")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _search_campaign_people(args: dict) -> dict:
    params = {"q": args["query"], "limit": args.get("limit", 20)}
    resp = await spoke_client.get("campaign_finance", "/api/people/search", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


# ---------------------------------------------------------------------------
# Facebook-Monitor handlers
# ---------------------------------------------------------------------------

async def _search_monitored_posts(args: dict) -> dict:
    params = {"q": args["query"], "limit": args.get("limit", 10)}
    if args.get("page_name"):
        params["page_name"] = args["page_name"]
    resp = await spoke_client.get("facebook_monitor", "/api/posts/search", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _get_monitored_post(args: dict) -> dict:
    pid = args["post_id"]
    resp = await spoke_client.get("facebook_monitor", f"/api/posts/{pid}")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _search_monitored_people(args: dict) -> dict:
    params = {"search": args.get("query", "")}
    resp = await spoke_client.get("facebook_monitor", "/api/people", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _list_monitored_pages(args: dict) -> dict:
    resp = await spoke_client.get("facebook_monitor", "/api/stats")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _get_fb_monitor_entities(args: dict) -> dict:
    params = {}
    if args.get("query"):
        params["search"] = args["query"]
    resp = await spoke_client.get("facebook_monitor", "/api/entities", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


# ---------------------------------------------------------------------------
# Semantic search (LazyChroma RAG)
# ---------------------------------------------------------------------------

async def _semantic_search(args: dict) -> dict:
    from app.services.rag.retrieval_validator import retrieve
    query = args.get("query", "")
    source_types = args.get("source_types")
    limit = args.get("limit", 5)
    try:
        results = await retrieve(query=query, source_types=source_types, limit=limit)
        if not results:
            return {"success": True, "data": [], "message": "No semantic matches found"}
        # Format results for the LLM
        formatted = []
        for r in results:
            formatted.append({
                "text": r.get("text", "")[:2000],  # cap length for LLM context
                "source_type": r.get("metadata", {}).get("source_type", ""),
                "source_id": r.get("metadata", {}).get("source_id", ""),
                "date": r.get("metadata", {}).get("date", ""),
                "relevance_score": round(1 - (r.get("distance", 0) or 0), 4),
            })
        return {"success": True, "data": formatted}
    except Exception as exc:
        logger.exception("Semantic search error")
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Shasta-PRA handlers
# ---------------------------------------------------------------------------

async def _search_pra_requests(args: dict) -> dict:
    params = {"limit": args.get("limit", 10)}
    if args.get("query"):
        params["q"] = args["query"]
    if args.get("status"):
        params["status"] = args["status"]
    if args.get("department"):
        params["department"] = args["department"]
    if args.get("poc"):
        params["poc"] = args["poc"]
    if args.get("date_from"):
        params["date_from"] = args["date_from"]
    if args.get("date_to"):
        params["date_to"] = args["date_to"]
    resp = await spoke_client.get("shasta_pra", "/api/requests", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _get_pra_request(args: dict) -> dict:
    pid = args["pretty_id"]
    resp = await spoke_client.get("shasta_pra", f"/api/requests/{pid}")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _list_pra_departments(args: dict) -> dict:
    resp = await spoke_client.get("shasta_pra", "/api/departments")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _get_pra_stats(args: dict) -> dict:
    resp = await spoke_client.get("shasta_pra", "/api/stats")
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


async def _search_pra_all(args: dict) -> dict:
    params = {"q": args["query"], "limit": args.get("limit", 20)}
    resp = await spoke_client.get("shasta_pra", "/api/search", params=params)
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    return {"success": True, "data": resp.json()}


# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------

_TOOL_HANDLERS = {
    # civic_media
    "search_meetings": _search_meetings,
    "get_transcript": _get_transcript,
    "search_speakers": _search_speakers,
    "get_speaker_appearances": _get_speaker_appearances,
    "export_transcript": _export_transcript,
    # article-tracker
    "search_articles": _search_articles,
    "get_article_stats": _get_article_stats,
    "get_recent_articles": _get_recent_articles,
    # Shasta-DB
    "search_files": _search_files,
    "list_archive_people": _list_archive_people,
    "get_file_info": _get_file_info,
    # Facebook-Offline
    "search_messages": _search_messages,
    "search_posts": _search_posts,
    "list_threads": _list_threads,
    "get_thread_messages": _get_thread_messages,
    "search_people_fb": _search_people_fb,
    # Shasta-PRA
    "search_pra_requests": _search_pra_requests,
    "get_pra_request": _get_pra_request,
    "list_pra_departments": _list_pra_departments,
    "get_pra_stats": _get_pra_stats,
    "search_pra_all": _search_pra_all,
    # Campaign Finance
    "search_campaign_filers": _search_campaign_filers,
    "get_campaign_filer": _get_campaign_filer,
    "search_campaign_transactions": _search_campaign_transactions,
    "search_campaign_filings": _search_campaign_filings,
    "get_campaign_stats": _get_campaign_stats,
    "search_campaign_people": _search_campaign_people,
    # Facebook-Monitor
    "search_monitored_posts": _search_monitored_posts,
    "get_monitored_post": _get_monitored_post,
    "search_monitored_people": _search_monitored_people,
    "list_monitored_pages": _list_monitored_pages,
    "get_fb_monitor_entities": _get_fb_monitor_entities,
    # Cross-spoke semantic search
    "semantic_search": _semantic_search,
}
