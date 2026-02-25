"""Per-spoke schema context for LLM system prompt injection.

Injected after classification based on which spokes matched.  The goal is to
give the LLM enough structural knowledge to use tools correctly on the first
attempt: valid enum values, primary key formats, join patterns, and the right
tool-chaining sequences for common research questions.

Keep blocks concise — this is operational context, not a full schema dump.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Per-spoke schema blocks
# ---------------------------------------------------------------------------

SCHEMA_BLOCKS: dict[str, str] = {

    "civic_media": """\
## Schema: civic_media — Government Meetings, Transcripts, Votes & Brown Act Reference
Data: Transcribed Shasta County public meetings (Board of Supervisors, City Council, Planning
Commission, etc.), radio/podcast audio, structured vote records parsed from meeting minutes,
and the Brown Act (CA open meetings law, stored section-by-section for lookup).

KEY ID FORMAT: meeting_id is a UUID string — always pass as string.
person_id is also a UUID string, not an integer.

MEETINGS:
- category: "meeting" (gov bodies) | "audio" (radio shows, KCNR, podcasts)
- governing_body: "Board of Supervisors" | "Redding City Council" | "Planning Commission" | etc.
- meeting_date: YYYY-MM-DD
- summary_short / summary_long: AI summaries — use to survey a meeting without reading full transcript

TRANSCRIPT SEGMENTS (one per spoken turn):
- text: transcribed speech, start_time/end_time in seconds
- Speaker resolved via segment_assignments → people (verified=True = human-confirmed)

MEETING VOTES (parsed from minutes PDFs — structured fact layer):
- One row per motion in meeting_votes; one row per supervisor in vote_members
- outcome: "Unanimously Carried" | "Carried" | "Failed" | "No Second" | etc.
- vote_value per member: "yes" | "no" | "abstain" | "absent"
- agenda_section: e.g. "Consent Calendar", "Regular Agenda"
- mover / seconder: supervisor last name

VOTE RESEARCH:
1. get_meeting_votes(meeting_id) → all votes for a specific meeting with per-supervisor breakdown
2. search_votes(member=name, vote_value="no", outcome=text, start_date=YYYY-MM-DD, end_date=YYYY-MM-DD,
   governing_body=text, section=text, limit=N) → cross-meeting vote search
   - member= matches supervisor last name (e.g. "Crye", "Long", "Moty")
   - vote_value= "yes"|"no"|"abstain"|"absent"
   - Use this to answer: "How did Supervisor X vote on Y?", "All dissenting votes this year"

BROWN ACT LOOKUP (CA open meetings law, stored by section):
- search_brown_act(query=text, limit=N) → returns matching statutory sections (§54950–§54963)
- Use when asked about: open meeting requirements, closed session rules, public comment rights,
  agenda posting deadlines, serial meeting prohibition, disruption/removal procedures
- Key sections: §54952.2=serial meetings, §54954.2=72hr agenda, §54954.3=public comment,
  §54956.9=closed session litigation, §54957.95=disruption/removal

MEETING SEARCH:
- search_meetings(query=term) → searches title, summary, governing body text
- To find a specific vote: search_meetings first to get meeting_id, then get_meeting_votes

PEOPLE RESEARCH:
1. search_speakers(query=name) → returns person_id (UUID string)
2. get_speaker_appearances(person_id) → all meetings where they spoke (person→meetings)
3. get_meeting_speakers(meeting_id) → all speakers at a specific meeting (meeting→people)
4. get_transcript(meeting_id) → full transcript with speaker assignments and timestamps

TOOL CHAINING EXAMPLES:
- "How did Crye vote on the CTCL grant?" → search_meetings("CTCL") → get_meeting_votes(meeting_id)
- "All of Crye's no votes in 2025" → search_votes(member="Crye", vote_value="no", start_date="2025-01-01")
- "What does the Brown Act say about closed sessions?" → search_brown_act("closed session")
- "Was there a Brown Act violation at this meeting?" → get_meeting_votes + search_brown_act for context""",

    "campaign_finance": """\
## Schema: campaign_finance — FPPC Campaign Finance (Shasta County, via NetFile)
Data: Campaign finance disclosures — filers, filings, and individual transactions.

CORE CHAIN: people → filer_people → filers → filings → transactions

FILERS (who files with FPPC):
- filer_type: "candidate" | "measure" | "pac" | "party"
- status: "active" | "terminated"
- A person may be a filer (candidate/treasurer) OR appear only as a donor in transactions

TRANSACTIONS (the money records):
- schedule meanings: "A"=monetary contributions IN, "B1"=loans received, "B2"=loan repayment,
  "C"=non-monetary contributions, "D"=independent expenditures, "E"=payments/expenditures OUT,
  "F"=accrued liabilities, "G"=loans made
- entity_type: "IND"=individual, "COM"=committee, "OTH"=other org, "PTY"=party, "SCC"=small contributor
- Key fields: entity_name, first_name, last_name, employer, occupation, city, state, amount, transaction_date

FILINGS: form_type values — "Form 460" (semi-annual), "Form 410" (registration),
"Form 496" (24-hour independent expenditure), "Form 497" (late contribution/expenditure)

PEOPLE RESEARCH:
- Is someone a candidate/filer? → search_campaign_filers(query=name)
- Did they donate? → search_campaign_transactions(query=name, schedule="A")
- Who donated TO them? → search_campaign_filers → search_campaign_transactions(query=candidate name, schedule="A")
- What did they spend? → search_campaign_transactions(query=name, schedule="E")
- Full person search (all roles): search_campaign_people(query=name) — returns both filer + transaction matches""",

    "article_tracker": """\
## Schema: article_tracker — Local News Archive (45+ sources)
Data: Articles from local, state, and national news covering Northern California civic affairs.

ARTICLES: full-text searchable via FTS5 index (headline, byline, description, article_text, tags)
- category: "ca02_local" | "north_state" | "california_state" | "progressive" | "mainstream_national"
- source_slug examples: "record-searchlight", "anewscafe", "krcr", "redding-com", "appeal-democrat"
- No person model — people appear in byline (authors) or named in article_text

PEOPLE RESEARCH:
- Coverage of a person: search_articles(query=name)
- By specific reporter/author: search_articles(query=reporter name)
- Recent local news: get_recent_articles(category="ca02_local") or category="north_state\"""",

    "shasta_pra": """\
## Schema: shasta_pra — Shasta County Public Records Requests (NextRequest portal)
Data: PRA/CPRA requests filed with Shasta County departments.

REQUESTS (primary record):
- pretty_id: string format "YY-NNN" e.g. "26-309" — THIS IS THE PRIMARY KEY, always pass as string
- request_state: "Closed" | "Open" | "Overdue"
- department_names: comma-separated string of departments involved
- poc_name: Point of Contact (county staff handling the request)
- requester_name / requester_email / requester_company: who filed

RELATED: timeline_events (request history), documents (attached files with OCR/transcription in document_text)

PEOPLE RESEARCH:
- Requests by/about a person: search_pra_requests(query=name) or search_pra_all(query=name) [searches docs too]
- Requests to a department: search_pra_requests(department="Planning")
- Open requests: search_pra_requests(status="Open")
- Full detail with timeline: get_pra_request(pretty_id="26-309")""",

    "facebook_monitor": """\
## Schema: facebook_monitor — Monitored Public Facebook Pages
Data: Posts and comments scraped from monitored public Facebook pages (public data only).

POSTS: page_name, author, text, detected_at, reaction_count, comment_count_text
COMMENTS: linked to posts; search_monitored_posts searches BOTH post text AND comment text
PEOPLE: tracked individuals — people_posts (roles: author/mentioned/tagged), people_comments
ENTITIES: organizations — entity_pages (pages they operate), entity_people (associated individuals)

PEOPLE RESEARCH:
- Find a person's activity: search_monitored_people(query=name) to find their ID, then search_monitored_posts(query=name)
- Posts from a specific page: search_monitored_posts(query=topic, page_name="PageName")
- Full post with all comments: get_monitored_post(post_id=id)
- Org and page connections: get_fb_monitor_entities(query=org name)""",

    "facebook_offline": """\
## Schema: facebook_offline — Personal Facebook Archive (STRICTLY PRIVATE)
Data: Personal Facebook messages and posts. ALL CONTENT IS PRIVATE PERSONAL DATA.
Only query when the user explicitly asks about their own private messages or posts.

THREADS: thread_type "inbox" | "archived" | "e2ee"; thread_participants links to people
MESSAGES: sender_id, content_type (text/photo/audio/video), sent_at datetime
PEOPLE: is_self=True for archive owner; aliases=JSON array of alternate names

RESEARCH:
- Messages about a topic: search_messages(query=topic)
- Messages with a contact: list_threads(query=person name) → get_thread_messages(thread_id)
- Personal posts: search_posts(query=topic)""",

    "shasta_db": """\
## Schema: shasta_db — Civic Media File Archive
Data: Catalog of civic media files (video, audio, documents, images) organized by directory roots.

INSTANCES (files): kind ("video"|"audio"|"document"|"image"|"other"), category, display_title, ext, rel_path
PEOPLE: tagged in files via instance_people; source can be "manual", "llm", "path", "ocr", "transcript"

RESEARCH:
- Find a file: search_files(query=term, kind="video") or search_files(ext="pdf")
- Files tagged with a person: list_archive_people(name=person) or search_files(query=person name)""",
}


# ---------------------------------------------------------------------------
# Cross-spoke people context — always injected when any spokes are active
# ---------------------------------------------------------------------------

CROSS_SPOKE_PEOPLE_CONTEXT = """\
## Cross-Spoke Person Research
A person in this civic ecosystem may appear across multiple independent databases.

PERSON ACTIVITY MAP:
- civic_media      → Did they speak at meetings or on radio shows?
- campaign_finance → Did they donate, run for office, operate a PAC, or receive expenditures?
- article_tracker  → Are they mentioned in or writing local news?
- shasta_pra       → Did they file public records requests or appear in PRA documents?
- facebook_monitor → Do they post on or operate monitored public Facebook pages?
- facebook_offline → Are they in personal messages? (private — only when explicitly requested)
- shasta_db        → Are they tagged in archived civic media files?

RESEARCH WORKFLOW:
1. search_atlas_people(query=name) — Atlas unified directory; shows which spokes have a record for this person
2. Fan out to each spoke that has a match, using that spoke's person_id
3. For spokes without a unified record, search by name directly (person may exist but not yet be linked)
4. Synthesize findings across all spokes into a coherent profile

ATLAS UNIFIED PEOPLE:
- unified_people table maps one canonical identity across multiple spokes
- person_mappings stores (spoke_key, spoke_person_id, spoke_person_name) per spoke
- Example: "John Moorman" may be person_id=42 in civic_media AND filer_id="uuid-..." in campaign_finance
- search_atlas_people returns these cross-spoke IDs so you can query each spoke precisely"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_schema_context(spokes: list[str]) -> str:
    """
    Build schema context string for the given list of active spokes.

    Always includes the cross-spoke people guide when any spokes are active.
    Returns empty string when spokes is empty (chat-only mode).
    """
    if not spokes:
        return ""

    parts = ["## Data Schema Context\n"]
    for spoke in spokes:
        block = SCHEMA_BLOCKS.get(spoke)
        if block:
            parts.append(block)

    parts.append(CROSS_SPOKE_PEOPLE_CONTEXT)
    return "\n\n".join(parts)
