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
                    "type": "string",
                    "description": "The meeting UUID string e.g. 'f9077e9b-d0c1-4875-a482-bb6c77a96cde'",
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
        "description": (
            "Search for known speakers/people across civic meetings by name. "
            "Returns person_id, canonical_name, and voiceprint_count. "
            "Always follow up with get_speaker_appearances(person_id) to get their meeting history — "
            "do not stop after finding the person_id."
        ),
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
        "description": (
            "Get all meetings where a specific speaker has been identified, with meeting dates, "
            "titles, governing body, and segment counts. Use this immediately after search_speakers "
            "returns a person_id — this is what answers 'what meetings did X attend'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "person_id": {
                    "type": "string",
                    "description": "The person UUID string from civic_media (returned by search_speakers)",
                },
                "date_from": {
                    "type": "string",
                    "description": "Filter to meetings on or after this date (YYYY-MM-DD). Use to answer 'this year' or 'since ...' queries.",
                },
                "date_to": {
                    "type": "string",
                    "description": "Filter to meetings on or before this date (YYYY-MM-DD).",
                },
            },
            "required": ["person_id"],
        },
    },
}

GET_MEETING_SPEAKERS = {
    "type": "function",
    "function": {
        "name": "get_meeting_speakers",
        "description": (
            "Get the list of identified speakers at a specific meeting, with segment counts. "
            "Use this to find out who participated in a particular meeting. "
            "Returns speaker names, person IDs, and how many segments they were assigned."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_id": {
                    "type": "string",
                    "description": "The meeting UUID string e.g. 'f9077e9b-d0c1-4875-a482-bb6c77a96cde'",
                },
            },
            "required": ["meeting_id"],
        },
    },
}

GET_MEETING_VOTES = {
    "type": "function",
    "function": {
        "name": "get_meeting_votes",
        "description": (
            "Get all formal votes recorded in the official minutes for a specific meeting. "
            "Returns each motion with its outcome (Unanimously Carried, Carried, Failed, etc.), "
            "vote tally (e.g. 4-1), mover, seconder, and how each supervisor voted. "
            "Use this when a user asks how someone voted, what passed/failed, or wants "
            "the official vote record rather than the transcript summary."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_id": {
                    "type": "string",
                    "description": "The meeting UUID string",
                },
            },
            "required": ["meeting_id"],
        },
    },
}

SEARCH_VOTES = {
    "type": "function",
    "function": {
        "name": "search_votes",
        "description": (
            "Search vote records across meetings. Use this to answer questions like "
            "'how did Crye vote on budget items', 'show all failed motions in 2025', "
            "or 'what did Harmon vote no on'. Filters by supervisor name, vote value, "
            "outcome type, date range, or agenda section."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "member": {
                    "type": "string",
                    "description": "Supervisor last name to filter by",
                },
                "vote_value": {
                    "type": "string",
                    "enum": ["yes", "no", "abstain", "absent"],
                    "description": "Filter by how this member voted",
                },
                "outcome": {
                    "type": "string",
                    "description": "Outcome filter, e.g. 'Failed — No Second', 'Carried', 'Unanimously Carried'",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date YYYY-MM-DD",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date YYYY-MM-DD",
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

SEARCH_BROWN_ACT = {
    "type": "function",
    "function": {
        "name": "search_brown_act",
        "description": (
            "Search the Brown Act (California Government Code §54950–54963) by keyword "
            "or section number. Use this when a user asks what the Brown Act says about "
            "a specific topic, or when you need to reference a specific provision to "
            "explain a potential violation noted in a meeting summary."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keyword, topic, or section number (e.g. '54954.3', 'public comment', 'serial meeting')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max sections to return (default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
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
# Shasta-PRA tools
# ---------------------------------------------------------------------------

SEARCH_PRA_REQUESTS = {
    "type": "function",
    "function": {
        "name": "search_pra_requests",
        "description": "Search Shasta County public records requests by keyword, status, department, POC, or date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term for request text, ID, requester, or POC",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by request state (e.g., Closed, Open, Overdue)",
                },
                "department": {
                    "type": "string",
                    "description": "Filter by department name",
                },
                "poc": {
                    "type": "string",
                    "description": "Filter by point of contact name",
                },
                "date_from": {
                    "type": "string",
                    "description": "Start date YYYY-MM-DD",
                },
                "date_to": {
                    "type": "string",
                    "description": "End date YYYY-MM-DD",
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

GET_PRA_REQUEST = {
    "type": "function",
    "function": {
        "name": "get_pra_request",
        "description": "Get full details of a specific public records request by its pretty ID (e.g., '25-389'), including timeline and documents.",
        "parameters": {
            "type": "object",
            "properties": {
                "pretty_id": {
                    "type": "string",
                    "description": "The request pretty ID (e.g., '25-389')",
                },
            },
            "required": ["pretty_id"],
        },
    },
}

LIST_PRA_DEPARTMENTS = {
    "type": "function",
    "function": {
        "name": "list_pra_departments",
        "description": "List all Shasta County departments that process public records requests, with request counts.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

GET_PRA_STATS = {
    "type": "function",
    "function": {
        "name": "get_pra_stats",
        "description": "Get overview statistics for Shasta County public records requests: totals, status breakdown, department breakdown, requests by month.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

SEARCH_PRA_ALL = {
    "type": "function",
    "function": {
        "name": "search_pra_all",
        "description": "Full-text search across all PRA tables (requests, timeline events, documents).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results per category (default 20)",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    },
}

# ---------------------------------------------------------------------------
# Campaign Finance tools
# ---------------------------------------------------------------------------

SEARCH_CAMPAIGN_FILERS = {
    "type": "function",
    "function": {
        "name": "search_campaign_filers",
        "description": "Search campaign finance filers (candidates, PACs, committees) in Shasta County. Returns name, type, status, office, and filing dates.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search by filer name or FPPC ID",
                },
                "filer_type": {
                    "type": "string",
                    "enum": ["candidate", "measure", "pac", "party"],
                    "description": "Filter by filer type",
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

GET_CAMPAIGN_FILER = {
    "type": "function",
    "function": {
        "name": "get_campaign_filer",
        "description": "Get detailed info about a specific campaign filer including filing count, total contributions, and total expenditures.",
        "parameters": {
            "type": "object",
            "properties": {
                "filer_id": {
                    "type": "string",
                    "description": "The filer UUID",
                },
            },
            "required": ["filer_id"],
        },
    },
}

SEARCH_CAMPAIGN_TRANSACTIONS = {
    "type": "function",
    "function": {
        "name": "search_campaign_transactions",
        "description": "Search campaign finance transactions (contributions and expenditures). Filter by donor/payee name, amount range, date range, or schedule type.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search by entity name, employer, or description",
                },
                "schedule": {
                    "type": "string",
                    "description": "Filter by schedule (A=contributions, E=expenditures, C=non-monetary)",
                },
                "amount_min": {
                    "type": "string",
                    "description": "Minimum amount filter",
                },
                "amount_max": {
                    "type": "string",
                    "description": "Maximum amount filter",
                },
                "date_from": {
                    "type": "string",
                    "description": "Start date YYYY-MM-DD",
                },
                "date_to": {
                    "type": "string",
                    "description": "End date YYYY-MM-DD",
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

SEARCH_CAMPAIGN_FILINGS = {
    "type": "function",
    "function": {
        "name": "search_campaign_filings",
        "description": "Search campaign finance filings (Form 460, 410, 496, 497, etc.) by form type, filer, or date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search by form name or type",
                },
                "form_type": {
                    "type": "string",
                    "description": "Filter by form type (e.g., 'Form 460')",
                },
                "filer_id": {
                    "type": "string",
                    "description": "Filter by filer UUID",
                },
                "date_from": {
                    "type": "string",
                    "description": "Start date YYYY-MM-DD",
                },
                "date_to": {
                    "type": "string",
                    "description": "End date YYYY-MM-DD",
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

GET_CAMPAIGN_STATS = {
    "type": "function",
    "function": {
        "name": "get_campaign_stats",
        "description": "Get campaign finance statistics: total filers, filings, transactions, contributions, expenditures, elections.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

SEARCH_CAMPAIGN_PEOPLE = {
    "type": "function",
    "function": {
        "name": "search_campaign_people",
        "description": "Search people in the campaign finance system — candidates, treasurers, donors, and payees.",
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
# Facebook-Monitor tools
# ---------------------------------------------------------------------------

SEARCH_MONITORED_POSTS = {
    "type": "function",
    "function": {
        "name": "search_monitored_posts",
        "description": "Search posts collected from monitored public Facebook pages. Returns posts with comments, page name, author, and engagement data.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term to find in posts and comments",
                },
                "page_name": {
                    "type": "string",
                    "description": "Filter by Facebook page name",
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

GET_MONITORED_POST = {
    "type": "function",
    "function": {
        "name": "get_monitored_post",
        "description": "Get a specific monitored Facebook post with its comments, attachments, and linked people.",
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "The Facebook post ID",
                },
            },
            "required": ["post_id"],
        },
    },
}

SEARCH_MONITORED_PEOPLE = {
    "type": "function",
    "function": {
        "name": "search_monitored_people",
        "description": "Search people tracked across monitored Facebook pages (post authors, commenters, page operators).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Name to search for",
                },
            },
            "required": ["query"],
        },
    },
}

LIST_MONITORED_PAGES = {
    "type": "function",
    "function": {
        "name": "list_monitored_pages",
        "description": "Get statistics about the Facebook Monitor: total posts, comments, monitored pages, tracked people, and entities.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

GET_FB_MONITOR_ENTITIES = {
    "type": "function",
    "function": {
        "name": "get_fb_monitor_entities",
        "description": "Search entities (organizations/groups) tracked in the Facebook Monitor, with linked pages and people.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Entity name to search for",
                },
            },
            "required": [],
        },
    },
}


# ---------------------------------------------------------------------------
# Atlas unified people search (cross-spoke identity)
# ---------------------------------------------------------------------------

SEARCH_ATLAS_PEOPLE = {
    "type": "function",
    "function": {
        "name": "search_atlas_people",
        "description": (
            "Search Atlas's unified person directory. Returns which spokes have a record for this person "
            "and their spoke-specific IDs, so you can query each spoke precisely. "
            "Use this as the FIRST step when researching a person — it tells you where to look next."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Person name or partial name to search for",
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
                        "enum": ["civic_media", "article_tracker", "shasta_db", "facebook_offline", "shasta_pra", "facebook_monitor", "campaign_finance"],
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

CIVIC_MEDIA_TOOLS = [SEARCH_MEETINGS, GET_TRANSCRIPT, SEARCH_SPEAKERS, GET_SPEAKER_APPEARANCES, GET_MEETING_SPEAKERS, EXPORT_TRANSCRIPT, GET_MEETING_VOTES, SEARCH_VOTES, SEARCH_BROWN_ACT]
ARTICLE_TRACKER_TOOLS = [SEARCH_ARTICLES, GET_ARTICLE_STATS, GET_RECENT_ARTICLES]
SHASTA_DB_TOOLS = [SEARCH_FILES, LIST_ARCHIVE_PEOPLE, GET_FILE_INFO]
FACEBOOK_OFFLINE_TOOLS = [SEARCH_MESSAGES, SEARCH_POSTS, LIST_THREADS, GET_THREAD_MESSAGES, SEARCH_PEOPLE_FB]
SHASTA_PRA_TOOLS = [SEARCH_PRA_REQUESTS, GET_PRA_REQUEST, LIST_PRA_DEPARTMENTS, GET_PRA_STATS, SEARCH_PRA_ALL]
FACEBOOK_MONITOR_TOOLS = [SEARCH_MONITORED_POSTS, GET_MONITORED_POST, SEARCH_MONITORED_PEOPLE, LIST_MONITORED_PAGES, GET_FB_MONITOR_ENTITIES]
CAMPAIGN_FINANCE_TOOLS = [SEARCH_CAMPAIGN_FILERS, GET_CAMPAIGN_FILER, SEARCH_CAMPAIGN_TRANSACTIONS, SEARCH_CAMPAIGN_FILINGS, GET_CAMPAIGN_STATS, SEARCH_CAMPAIGN_PEOPLE]

ATLAS_TOOLS = [SEARCH_ATLAS_PEOPLE, SEMANTIC_SEARCH]

ALL_TOOLS = CIVIC_MEDIA_TOOLS + ARTICLE_TRACKER_TOOLS + SHASTA_DB_TOOLS + FACEBOOK_OFFLINE_TOOLS + SHASTA_PRA_TOOLS + FACEBOOK_MONITOR_TOOLS + CAMPAIGN_FINANCE_TOOLS + ATLAS_TOOLS

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
for tool in SHASTA_PRA_TOOLS:
    TOOL_TO_SPOKE[tool["function"]["name"]] = "shasta_pra"
for tool in FACEBOOK_MONITOR_TOOLS:
    TOOL_TO_SPOKE[tool["function"]["name"]] = "facebook_monitor"
for tool in CAMPAIGN_FINANCE_TOOLS:
    TOOL_TO_SPOKE[tool["function"]["name"]] = "campaign_finance"
