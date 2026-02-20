"""Cross-app person resolution — search all spokes, match by name, build unified profiles."""

from __future__ import annotations

import asyncio
import logging
from difflib import SequenceMatcher

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
                params["search"] = query
            resp = await spoke_client.get("civic_media", "/api/people", params=params)
            if resp.status_code == 200:
                people = resp.json()
                return [{"spoke": "civic_media", "id": str(p["id"]), "name": p.get("name", ""), "extra": p} for p in people]
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
