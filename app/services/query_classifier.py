"""Query classifier — rule-based first pass, falls through to LLM for ambiguous queries."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.tools import (
    CIVIC_MEDIA_TOOLS, ARTICLE_TRACKER_TOOLS, SHASTA_DB_TOOLS, FACEBOOK_OFFLINE_TOOLS, ALL_TOOLS,
)


@dataclass
class Classification:
    spokes: list[str]           # which spoke(s) to query
    tools: list[dict]           # tool schemas to provide to the LLM
    profile: str                # suggested LLM profile: "fast", "quality", "code"
    confidence: float           # 0-1 confidence in the classification


# Keyword → spoke mapping (case-insensitive)
_SPOKE_KEYWORDS: dict[str, list[str]] = {
    "civic_media": [
        "meeting", "meetings", "transcript", "transcripts", "speaker", "speakers",
        "diarization", "voiceprint", "council", "commission", "agenda", "minutes",
        "public comment", "city council", "planning commission", "board of supervisors",
    ],
    "article_tracker": [
        "article", "articles", "news", "headline", "headlines", "reporter",
        "journalist", "source", "press", "media coverage", "story", "stories",
        "newspaper", "record searchlight", "krcr", "anewscafe",
    ],
    "shasta_db": [
        "archive", "archived", "file", "files", "video file", "recording",
        "shasta", "media file", "document", "browse", "catalog",
    ],
    "facebook_offline": [
        "facebook", "fb", "message", "messages", "messenger", "post", "posts",
        "thread", "conversation", "chat", "dm", "inbox",
    ],
}

# Profile selection keywords
_QUALITY_KEYWORDS = [
    "analyze", "explain", "summarize", "compare", "assessment", "detail",
    "comprehensive", "thorough", "deep dive", "what do you think",
]

_CODE_KEYWORDS = [
    "code", "api", "endpoint", "schema", "sql", "query", "function",
    "debug", "error", "stack trace", "implement",
]


def classify(query: str) -> Classification:
    """
    Classify a user query to determine which spokes and tools to use.

    Uses keyword matching first. If no spoke matches, returns all tools
    for LLM-based routing.
    """
    query_lower = query.lower()

    # Score each spoke
    spoke_scores: dict[str, int] = {}
    for spoke, keywords in _SPOKE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            spoke_scores[spoke] = score

    # Select matched spokes
    if spoke_scores:
        # Sort by score descending, take top spokes
        sorted_spokes = sorted(spoke_scores.items(), key=lambda x: x[1], reverse=True)
        # Take all spokes with scores within 50% of the top score
        top_score = sorted_spokes[0][1]
        matched_spokes = [s for s, score in sorted_spokes if score >= top_score * 0.5]
    else:
        matched_spokes = []

    # Build tool set
    if matched_spokes:
        tools = []
        for spoke in matched_spokes:
            tools.extend(_SPOKE_TOOLS[spoke])
        confidence = min(0.9, 0.5 + 0.1 * sum(spoke_scores.values()))
    else:
        # No keyword match — give LLM all tools to decide
        tools = ALL_TOOLS
        matched_spokes = list(_SPOKE_KEYWORDS.keys())
        confidence = 0.3

    # Select profile
    profile = _select_profile(query_lower)

    return Classification(
        spokes=matched_spokes,
        tools=tools,
        profile=profile,
        confidence=confidence,
    )


def _select_profile(query_lower: str) -> str:
    """Pick LLM profile based on query complexity."""
    if any(kw in query_lower for kw in _CODE_KEYWORDS):
        return "code"
    if any(kw in query_lower for kw in _QUALITY_KEYWORDS):
        return "quality"
    return "fast"


_SPOKE_TOOLS = {
    "civic_media": CIVIC_MEDIA_TOOLS,
    "article_tracker": ARTICLE_TRACKER_TOOLS,
    "shasta_db": SHASTA_DB_TOOLS,
    "facebook_offline": FACEBOOK_OFFLINE_TOOLS,
}
