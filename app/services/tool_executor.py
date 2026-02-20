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

    spoke_key = TOOL_TO_SPOKE.get(name)
    if not spoke_key:
        return {"success": False, "error": f"Unknown tool: {name}"}

    try:
        handler = _TOOL_HANDLERS.get(name)
        if not handler:
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
}
