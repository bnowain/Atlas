"""OpenAI function-calling tool schemas for each spoke's capabilities."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# civic_media tools
# ---------------------------------------------------------------------------

SEARCH_MEETINGS = {
    "type": "function",
    "function": {
        "name": "search_meetings",
        "description": "Search civic meeting transcripts. Returns meetings with titles, dates, and segment counts.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term to find in meeting titles or transcripts",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 10)",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
}

GET_TRANSCRIPT = {
    "type": "function",
    "function": {
        "name": "get_transcript",
        "description": "Get the full transcript for a specific meeting, including speaker assignments and timestamps.",
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_id": {
                    "type": "integer",
                    "description": "The meeting ID",
                },
            },
            "required": ["meeting_id"],
        },
    },
}

SEARCH_SPEAKERS = {
    "type": "function",
    "function": {
        "name": "search_speakers",
        "description": "Search for known speakers/people across civic meetings. Returns names, voiceprint counts, and IDs.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Name or partial name to search for",
                },
            },
            "required": [],
        },
    },
}

GET_SPEAKER_APPEARANCES = {
    "type": "function",
    "function": {
        "name": "get_speaker_appearances",
        "description": "Get all meetings where a specific speaker has been identified, with segment counts per meeting.",
        "parameters": {
            "type": "object",
            "properties": {
                "person_id": {
                    "type": "integer",
                    "description": "The person ID from civic_media",
                },
            },
            "required": ["person_id"],
        },
    },
}

EXPORT_TRANSCRIPT = {
    "type": "function",
    "function": {
        "name": "export_transcript",
        "description": "Export a meeting transcript in a specific format (srt, txt, or json).",
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_id": {
                    "type": "integer",
                    "description": "The meeting ID",
                },
                "format": {
                    "type": "string",
                    "enum": ["srt", "txt", "json"],
                    "description": "Export format",
                    "default": "txt",
                },
            },
            "required": ["meeting_id"],
        },
    },
}

# ---------------------------------------------------------------------------
# article-tracker tools
# ---------------------------------------------------------------------------

SEARCH_ARTICLES = {
    "type": "function",
    "function": {
        "name": "search_articles",
        "description": "Search local news articles by keyword. Returns titles, sources, dates, and snippets.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term",
                },
                "category": {
                    "type": "string",
                    "description": "Filter by category (progressive, mainstream_national, california_state, ca02_local, north_state)",
                },
                "source": {
                    "type": "string",
                    "description": "Filter by source slug",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
}

GET_ARTICLE_STATS = {
    "type": "function",
    "function": {
        "name": "get_article_stats",
        "description": "Get statistics about the article tracker: total articles, total sources.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

GET_RECENT_ARTICLES = {
    "type": "function",
    "function": {
        "name": "get_recent_articles",
        "description": "Get the most recent articles, optionally filtered by category or source.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category",
                },
                "source": {
                    "type": "string",
                    "description": "Filter by source slug",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
}

# ---------------------------------------------------------------------------
# Shasta-DB tools
# ---------------------------------------------------------------------------

SEARCH_FILES = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": "Search the Shasta-DB civic media archive by keyword, file type, or extension.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term for file titles/metadata",
                },
                "kind": {
                    "type": "string",
                    "description": "File kind filter (e.g., video, audio, document)",
                },
                "ext": {
                    "type": "string",
                    "description": "File extension filter (e.g., mp4, pdf)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 20)",
                    "default": 20,
                },
            },
            "required": [],
        },
    },
}

LIST_ARCHIVE_PEOPLE = {
    "type": "function",
    "function": {
        "name": "list_archive_people",
        "description": "List people tagged in the Shasta-DB archive, optionally filtered by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Filter by name (partial match)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 50)",
                    "default": 50,
                },
            },
            "required": [],
        },
    },
}

GET_FILE_INFO = {
    "type": "function",
    "function": {
        "name": "get_file_info",
        "description": "Get detailed metadata about a specific file in the Shasta-DB archive.",
        "parameters": {
            "type": "object",
            "properties": {
                "instance_id": {
                    "type": "integer",
                    "description": "The file instance ID in Shasta-DB",
                },
            },
            "required": ["instance_id"],
        },
    },
}

# ---------------------------------------------------------------------------
# Facebook-Offline tools
# ---------------------------------------------------------------------------

SEARCH_MESSAGES = {
    "type": "function",
    "function": {
        "name": "search_messages",
        "description": "Search personal Facebook messages by keyword. Treat results as private.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term",
                },
                "thread_id": {
                    "type": "integer",
                    "description": "Limit to a specific conversation thread",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
}

SEARCH_POSTS = {
    "type": "function",
    "function": {
        "name": "search_posts",
        "description": "Search personal Facebook posts by keyword. Treat results as private.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
}

LIST_THREADS = {
    "type": "function",
    "function": {
        "name": "list_threads",
        "description": "List Facebook conversation threads, optionally filtered by participant name.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Filter by participant name or thread title",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 20)",
                    "default": 20,
                },
            },
            "required": [],
        },
    },
}

GET_THREAD_MESSAGES = {
    "type": "function",
    "function": {
        "name": "get_thread_messages",
        "description": "Get messages from a specific Facebook conversation thread.",
        "parameters": {
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "integer",
                    "description": "The thread ID",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max messages to return (default 50)",
                    "default": 50,
                },
            },
            "required": ["thread_id"],
        },
    },
}

SEARCH_PEOPLE_FB = {
    "type": "function",
    "function": {
        "name": "search_people_fb",
        "description": "Search people in the Facebook archive by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Name to search for",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 20)",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    },
}


# ---------------------------------------------------------------------------
# Cross-spoke semantic search (LazyChroma RAG)
# ---------------------------------------------------------------------------

SEMANTIC_SEARCH = {
    "type": "function",
    "function": {
        "name": "semantic_search",
        "description": "Semantic search across civic data sources. Use for finding relevant content by meaning rather than exact keywords. Returns ranked chunks with source references.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "source_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["civic_media", "article_tracker", "shasta_db", "facebook_offline"],
                    },
                    "description": "Which data sources to search (default: all active)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}

# ---------------------------------------------------------------------------
# Aggregated tool sets
# ---------------------------------------------------------------------------

CIVIC_MEDIA_TOOLS = [SEARCH_MEETINGS, GET_TRANSCRIPT, SEARCH_SPEAKERS, GET_SPEAKER_APPEARANCES, EXPORT_TRANSCRIPT]
ARTICLE_TRACKER_TOOLS = [SEARCH_ARTICLES, GET_ARTICLE_STATS, GET_RECENT_ARTICLES]
SHASTA_DB_TOOLS = [SEARCH_FILES, LIST_ARCHIVE_PEOPLE, GET_FILE_INFO]
FACEBOOK_OFFLINE_TOOLS = [SEARCH_MESSAGES, SEARCH_POSTS, LIST_THREADS, GET_THREAD_MESSAGES, SEARCH_PEOPLE_FB]

ALL_TOOLS = CIVIC_MEDIA_TOOLS + ARTICLE_TRACKER_TOOLS + SHASTA_DB_TOOLS + FACEBOOK_OFFLINE_TOOLS

# Map tool name → spoke key for routing
TOOL_TO_SPOKE: dict[str, str] = {}
for tool in CIVIC_MEDIA_TOOLS:
    TOOL_TO_SPOKE[tool["function"]["name"]] = "civic_media"
for tool in ARTICLE_TRACKER_TOOLS:
    TOOL_TO_SPOKE[tool["function"]["name"]] = "article_tracker"
for tool in SHASTA_DB_TOOLS:
    TOOL_TO_SPOKE[tool["function"]["name"]] = "shasta_db"
for tool in FACEBOOK_OFFLINE_TOOLS:
    TOOL_TO_SPOKE[tool["function"]["name"]] = "facebook_offline"
