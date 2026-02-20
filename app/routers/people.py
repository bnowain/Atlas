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
async def list_people(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UnifiedPerson)
        .options(selectinload(UnifiedPerson.mappings))
        .order_by(UnifiedPerson.display_name)
    )
    return result.scalars().all()


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
