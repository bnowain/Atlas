"""Cross-app person resolution — search all spokes, match by name, build unified profiles."""

from __future__ import annotations

import asyncio
import logging
from difflib import SequenceMatcher
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UnifiedPerson, PersonMapping
from app.services import spoke_client

logger = logging.getLogger(__name__)


async def discover_people(db: AsyncSession, name: str | None = None) -> list[dict]:
    """Search all spokes' people endpoints and return aggregated results."""
    tasks = []

    async def _fetch_civic_media(query: str | None):
        try:
            params = {}
            if query:
                params["q"] = query
            resp = await spoke_client.get("civic_media", "/api/people/", params=params)
            if resp.status_code == 200:
                people = resp.json()
                return [{"spoke": "civic_media", "id": str(p["person_id"]), "name": p.get("canonical_name", ""), "extra": p} for p in people]
        except Exception:
            pass
        return []

    async def _fetch_shasta_db(query: str | None):
        try:
            params = {"limit": "50"}
            if query:
                params["name"] = query
            resp = await spoke_client.get("shasta_db", "/people", params=params)
            if resp.status_code == 200:
                people = resp.json()
                if isinstance(people, list):
                    return [{"spoke": "shasta_db", "id": str(p.get("id", "")), "name": p.get("name", ""), "extra": p} for p in people]
        except Exception:
            pass
        return []

    async def _fetch_facebook(query: str | None):
        try:
            params = {"limit": "50"}
            if query:
                params["q"] = query
            resp = await spoke_client.get("facebook_offline", "/api/people", params=params)
            if resp.status_code == 200:
                data = resp.json()
                people = data if isinstance(data, list) else data.get("items", [])
                return [{"spoke": "facebook_offline", "id": str(p.get("id", "")), "name": p.get("name", ""), "extra": p} for p in people]
        except Exception:
            pass
        return []

    results = await asyncio.gather(
        _fetch_civic_media(name),
        _fetch_shasta_db(name),
        _fetch_facebook(name),
    )

    all_people = []
    for group in results:
        all_people.extend(group)

    return all_people


def match_people(people: list[dict], threshold: float = 0.8) -> list[list[dict]]:
    """Group people from different spokes by name similarity."""
    used = set()
    groups = []

    for i, p1 in enumerate(people):
        if i in used:
            continue
        group = [p1]
        used.add(i)

        for j, p2 in enumerate(people):
            if j in used or p1["spoke"] == p2["spoke"]:
                continue
            sim = _name_similarity(p1["name"], p2["name"])
            if sim >= threshold:
                group.append(p2)
                used.add(j)

        groups.append(group)

    return groups


def _name_similarity(a: str, b: str) -> float:
    """Compare two names with case-insensitive matching."""
    a_norm = a.strip().lower()
    b_norm = b.strip().lower()
    if a_norm == b_norm:
        return 1.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


async def get_unified_people(db: AsyncSession) -> list[UnifiedPerson]:
    result = await db.execute(select(UnifiedPerson).order_by(UnifiedPerson.display_name))
    return list(result.scalars().all())


async def get_unified_person(db: AsyncSession, person_id: int) -> UnifiedPerson | None:
    return await db.get(UnifiedPerson, person_id)


async def create_unified_person(
    db: AsyncSession,
    display_name: str,
    notes: str | None = None,
) -> UnifiedPerson:
    person = UnifiedPerson(display_name=display_name, notes=notes)
    db.add(person)
    await db.commit()
    await db.refresh(person)
    return person


async def link_person(
    db: AsyncSession,
    unified_person_id: int,
    spoke_key: str,
    spoke_person_id: str,
    spoke_person_name: str | None = None,
) -> PersonMapping:
    mapping = PersonMapping(
        unified_person_id=unified_person_id,
        spoke_key=spoke_key,
        spoke_person_id=spoke_person_id,
        spoke_person_name=spoke_person_name,
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return mapping


# ---------------------------------------------------------------------------
# Spoke sync fetchers — each returns list[{spoke_person_id, canonical_name}]
# ---------------------------------------------------------------------------

# Names in civic_media that are annotation markers, not real people.
# "Ignore" is used to tag pastor invocations, commercials, and other segments
# that should be excluded from speaker attribution entirely.
_CIVIC_MEDIA_SKIP_NAMES = {"ignore", "unknown", "unknown speaker"}


async def _sync_fetch_civic_media() -> list[dict]:
    """Fetch all people from civic_media for sync, excluding annotation markers."""
    resp = await spoke_client.get("civic_media", "/api/people/")
    if resp.status_code != 200:
        raise RuntimeError(f"civic_media /api/people/ returned HTTP {resp.status_code}")
    people = resp.json()
    return [
        {
            "spoke_person_id": str(p["person_id"]),
            "canonical_name": p.get("canonical_name", ""),
        }
        for p in people
        if p.get("person_id")
        and p.get("canonical_name")
        and p["canonical_name"].strip().lower() not in _CIVIC_MEDIA_SKIP_NAMES
    ]


_SPOKE_SYNC_FETCHERS = {
    "civic_media": _sync_fetch_civic_media,
}


async def sync_from_spoke(db: AsyncSession, spoke_key: str) -> dict:
    """
    Sync all people from a spoke into unified_people + person_mappings.

    Strategy:
    - If mapping already exists → update spoke_person_name if changed
    - If no mapping → create new UnifiedPerson + PersonMapping

    Returns: {spoke_key, total_fetched, created, updated, unchanged}
    """
    fetcher = _SPOKE_SYNC_FETCHERS.get(spoke_key)
    if fetcher is None:
        raise ValueError(f"No sync fetcher for spoke: {spoke_key}")

    spoke_people = await fetcher()

    # Load all existing mappings for this spoke into a lookup dict
    result = await db.execute(
        select(PersonMapping).where(PersonMapping.spoke_key == spoke_key)
    )
    existing_mappings: dict[str, PersonMapping] = {
        m.spoke_person_id: m for m in result.scalars().all()
    }

    created = 0
    updated = 0
    unchanged = 0

    for person_data in spoke_people:
        sid = person_data["spoke_person_id"]
        name = person_data["canonical_name"]

        if sid in existing_mappings:
            mapping = existing_mappings[sid]
            if mapping.spoke_person_name != name:
                mapping.spoke_person_name = name
                # Also update the unified person's display_name
                unified = await db.get(UnifiedPerson, mapping.unified_person_id)
                if unified:
                    unified.display_name = name
                    unified.updated_at = datetime.now(timezone.utc)
                updated += 1
            else:
                unchanged += 1
        else:
            # New person — create UnifiedPerson + PersonMapping
            unified = UnifiedPerson(display_name=name)
            db.add(unified)
            await db.flush()  # get the auto-generated id

            mapping = PersonMapping(
                unified_person_id=unified.id,
                spoke_key=spoke_key,
                spoke_person_id=sid,
                spoke_person_name=name,
            )
            db.add(mapping)
            created += 1

    await db.commit()

    return {
        "spoke_key": spoke_key,
        "total_fetched": len(spoke_people),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
    }
