"""Unified person directory — cross-app identity resolution."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.database import get_db
from app.models import UnifiedPerson
from app.schemas import UnifiedPersonResponse, PersonLinkRequest
from app.services import person_resolver

router = APIRouter(prefix="/api/people", tags=["people"])


@router.get("", response_model=list[UnifiedPersonResponse])
async def list_people(q: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(UnifiedPerson)
        .options(selectinload(UnifiedPerson.mappings))
        .order_by(UnifiedPerson.display_name)
    )
    result = await db.execute(stmt)
    people = result.scalars().all()
    if q:
        q_lower = q.lower()
        people = [p for p in people if q_lower in p.display_name.lower()]
    return people


@router.post("/sync/{spoke_key}")
async def sync_people(spoke_key: str, db: AsyncSession = Depends(get_db)):
    """Sync all people from a spoke into the unified people index."""
    try:
        stats = await person_resolver.sync_from_spoke(db, spoke_key)
        return stats
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"Sync failed: {exc}")


@router.get("/discover")
async def discover_people(name: str | None = None, db: AsyncSession = Depends(get_db)):
    """Search all spokes for people, return aggregated results."""
    people = await person_resolver.discover_people(db, name)
    return {"people": people, "total": len(people)}


@router.get("/{person_id}", response_model=UnifiedPersonResponse)
async def get_person(person_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UnifiedPerson)
        .where(UnifiedPerson.id == person_id)
        .options(selectinload(UnifiedPerson.mappings))
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")
    return person


@router.post("", response_model=UnifiedPersonResponse, status_code=201)
async def create_person(display_name: str, notes: str | None = None, db: AsyncSession = Depends(get_db)):
    person = await person_resolver.create_unified_person(db, display_name, notes)
    return person


@router.delete("/{person_id}", status_code=204)
async def delete_person(person_id: int, db: AsyncSession = Depends(get_db)):
    person = await db.get(UnifiedPerson, person_id)
    if not person:
        raise HTTPException(404, "Person not found")
    await db.delete(person)
    await db.commit()


@router.post("/{person_id}/link")
async def link_person(
    person_id: int,
    req: PersonLinkRequest,
    db: AsyncSession = Depends(get_db),
):
    person = await db.get(UnifiedPerson, person_id)
    if not person:
        raise HTTPException(404, "Person not found")

    mapping = await person_resolver.link_person(
        db,
        unified_person_id=person_id,
        spoke_key=req.spoke_key,
        spoke_person_id=req.spoke_person_id,
        spoke_person_name=req.spoke_person_name,
    )
    return {"status": "linked", "mapping_id": mapping.id}
