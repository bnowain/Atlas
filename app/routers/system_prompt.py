"""System prompt management — GET/PUT the base prompt stored in the DB."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import BaseSystemPromptResponse, BaseSystemPromptUpdate
from app.services import system_prompt_manager

router = APIRouter(prefix="/api/system-prompt", tags=["system-prompt"])


@router.get("", response_model=BaseSystemPromptResponse)
async def get_system_prompt(db: AsyncSession = Depends(get_db)):
    """Return the current base system prompt, seeding from default if not yet stored."""
    row = await system_prompt_manager.get_or_seed_system_prompt(db)
    return row


@router.put("", response_model=BaseSystemPromptResponse)
async def update_system_prompt(
    payload: BaseSystemPromptUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update the base system prompt."""
    row = await system_prompt_manager.update_system_prompt(db, payload.content)
    return row
