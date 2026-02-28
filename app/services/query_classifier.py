"""Query classifier — rule-based first pass, falls through to LLM for ambiguous queries."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.tools import (
    CIVIC_MEDIA_TOOLS, ARTICLE_TRACKER_TOOLS, SHASTA_DB_TOOLS, FACEBOOK_OFFLINE_TOOLS,
    SHASTA_PRA_TOOLS, FACEBOOK_MONITOR_TOOLS, CAMPAIGN_FINANCE_TOOLS, MISSION_CONTROL_TOOLS,
    ALL_TOOLS, SEMANTIC_SEARCH, SEARCH_ATLAS_PEOPLE,
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
        # votes / meeting minutes
        "vote", "votes", "voted", "voting", "motion", "resolution", "dissent",
        "rollcall", "roll call", "tally", "aye", "nay", "supervisor vote",
        "unanimously", "carried", "failed motion", "consent calendar",
        # Brown Act / open meetings law
        "brown act", "open meeting", "open meetings", "closed session", "serial meeting",
        "agenda posting", "public comment denied", "open government",
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
        "facebook", "fb", "message", "messages", "messenger",
        "thread", "conversation", "chat", "dm", "inbox",
    ],
    "shasta_pra": [
        "pra", "public record", "public records", "records request", "nextrequest",
        "foia", "cpra", "disclosure", "department", "requester",
    ],
    "facebook_monitor": [
        "monitored page", "facebook page", "page post", "page posts", "tracked page",
        "facebook monitor", "fb page", "commenter", "commenters", "engagement",
        "reaction", "shared post", "public post", "public posts",
    ],
    "campaign_finance": [
        "campaign", "campaign finance", "contribution", "contributions", "expenditure",
        "expenditures", "donor", "donors", "filer", "filers", "filing", "filings",
        "fppc", "form 460", "pac", "committee", "treasurer", "netfile",
        "election", "candidate", "ballot measure",
    ],
    "mission_control": [
        "mission control", "codex", "codex lesson", "ai lesson", "execution failure",
        "model failure", "llm failure", "retry", "retries", "escalation", "replan",
        "grading", "grading score", "routing", "model routing", "model performance",
        "context window", "context escalation", "token limit", "execution loop",
        "task failed", "ai execution", "pipeline failure", "worker", "artifact embedding",
        "rag search", "semantic search mission", "codebase index",
    ],
}

# Person-research keywords — trigger all spokes since a person can appear anywhere
_PERSON_RESEARCH_KEYWORDS = [
    "who is", "who was", "tell me about", "what do you know about", "profile of",
    "background on", "research", "anything on", "everything about", "find out about",
    "what has", "what did", "has anyone", "did anyone", "find everything",
]

# Profile selection keywords
_QUALITY_KEYWORDS = [
    "analyze", "explain", "summarize", "compare", "assessment", "detail",
    "comprehensive", "thorough", "deep dive", "what do you think",
]

_CODE_KEYWORDS = [
    "code", "api", "endpoint", "schema", "sql", "query", "function",
    "debug", "error", "stack trace", "implement",
]


def classify(query: str, allowed_spokes: list[str] | None = None) -> Classification:
    """
    Classify a user query to determine which spokes and tools to use.

    allowed_spokes controls which spokes may be used:
      - None  → keyword matching as normal (all spokes eligible)
      - []    → chat only, no tools
      - [...]  → only the listed spokes are eligible
    """
    # Chat-only mode: empty list means no tools at all
    if allowed_spokes is not None and len(allowed_spokes) == 0:
        return Classification(
            spokes=[],
            tools=[],
            profile=_select_profile(query.lower()),
            confidence=1.0,
        )

    query_lower = query.lower()

    # Check for person-research query (e.g. "who is X", "tell me about X")
    is_person_research = any(kw in query_lower for kw in _PERSON_RESEARCH_KEYWORDS)

    # Score each spoke (only consider allowed ones)
    spoke_scores: dict[str, int] = {}
    for spoke, keywords in _SPOKE_KEYWORDS.items():
        if allowed_spokes is not None and spoke not in allowed_spokes:
            continue
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            spoke_scores[spoke] = score

    # Select matched spokes
    if spoke_scores:
        sorted_spokes = sorted(spoke_scores.items(), key=lambda x: x[1], reverse=True)
        top_score = sorted_spokes[0][1]
        matched_spokes = [s for s, score in sorted_spokes if score >= top_score * 0.5]
    else:
        matched_spokes = []

    # Person-research queries expand to all spokes — a person can appear anywhere
    if is_person_research:
        all_allowed = list(_SPOKE_KEYWORDS.keys()) if allowed_spokes is None else allowed_spokes
        for spoke in all_allowed:
            if spoke not in matched_spokes:
                matched_spokes.append(spoke)

    # Build tool set
    if matched_spokes:
        tools = []
        for spoke in matched_spokes:
            tools.extend(_SPOKE_TOOLS[spoke])
        # Always include cross-spoke tools when any spokes are active
        tools.append(SEARCH_ATLAS_PEOPLE)
        tools.append(SEMANTIC_SEARCH)
        confidence = min(0.9, 0.5 + 0.1 * sum(spoke_scores.values()))
        if is_person_research:
            confidence = max(confidence, 0.8)
    else:
        # No keyword match — let the LLM answer from its own knowledge
        tools = []
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
    "shasta_pra": SHASTA_PRA_TOOLS,
    "facebook_monitor": FACEBOOK_MONITOR_TOOLS,
    "campaign_finance": CAMPAIGN_FINANCE_TOOLS,
    "mission_control": MISSION_CONTROL_TOOLS,
}
