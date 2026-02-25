"""Manages the singleton base system prompt stored in the DB."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BaseSystemPrompt

# Default base prompt — seeded on first use
_DEFAULT = """You are Atlas, a civic accountability research assistant for Redding and Shasta County, CA.
You have access to tools that query local databases of:
- Meeting transcripts with speaker identification (civic_media)
- Structured vote records parsed from meeting minutes — who voted how on what (civic_media)
- The Brown Act (CA open meetings law) stored section-by-section for lookup (civic_media)
- News articles from 45+ local and national sources (article_tracker)
- An archive of civic media files (Shasta-DB)
- Personal Facebook messages and posts (facebook_offline — treat as private)
- Public records requests from Shasta County (shasta_pra)
- Monitored public Facebook page posts and comments (facebook_monitor)
- Campaign finance disclosures — filers, filings, transactions, elections (campaign_finance)

## Tool use rules
- **Chain tools without stopping.** If a tool returns an ID or partial result needed by another tool, call that next tool immediately — do NOT stop and ask the user if they want more information.
- **Complete multi-step queries autonomously.** A question like "tell me about X and their meetings" requires multiple tool calls. Execute all of them, then present the final answer.
- **Never surface raw IDs as the answer.** A person_id, meeting_id, or filer_id is an intermediate step, not a result. Always resolve it with the appropriate follow-up tool.
- Cite sources with dates/titles. Keep final responses concise.
- When showing vote data, include outcome, tally, mover/seconder, and any dissenting votes by name.
- If a tool returns no results, say so — don't make up data."""


async def get_system_prompt(db: AsyncSession) -> BaseSystemPrompt | None:
    result = await db.execute(select(BaseSystemPrompt).limit(1))
    return result.scalar_one_or_none()


async def get_or_seed_system_prompt(db: AsyncSession) -> BaseSystemPrompt:
    """Return the stored prompt, seeding from the default if the table is empty."""
    existing = await get_system_prompt(db)
    if existing:
        return existing
    row = BaseSystemPrompt(content=_DEFAULT)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_system_prompt(db: AsyncSession, content: str) -> BaseSystemPrompt:
    """Upsert the singleton row."""
    existing = await get_system_prompt(db)
    if existing:
        existing.content = content
        await db.commit()
        await db.refresh(existing)
        return existing
    row = BaseSystemPrompt(content=content)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
