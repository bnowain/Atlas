"""CRUD for custom system instruction presets."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SystemInstruction

logger = logging.getLogger(__name__)


async def list_instructions(db: AsyncSession) -> list[SystemInstruction]:
    result = await db.execute(select(SystemInstruction).order_by(SystemInstruction.name))
    return list(result.scalars().all())


async def get_instruction(db: AsyncSession, instruction_id: int) -> SystemInstruction | None:
    return await db.get(SystemInstruction, instruction_id)


async def get_default_instruction(db: AsyncSession) -> SystemInstruction | None:
    result = await db.execute(
        select(SystemInstruction).where(SystemInstruction.is_default == True)
    )
    return result.scalar_one_or_none()


async def create_instruction(
    db: AsyncSession,
    name: str,
    content: str,
    is_default: bool = False,
) -> SystemInstruction:
    if is_default:
        await _clear_defaults(db)

    instruction = SystemInstruction(
        name=name,
        content=content,
        is_default=is_default,
    )
    db.add(instruction)
    await db.commit()
    await db.refresh(instruction)
    return instruction


async def update_instruction(
    db: AsyncSession,
    instruction_id: int,
    **kwargs,
) -> SystemInstruction | None:
    instruction = await db.get(SystemInstruction, instruction_id)
    if not instruction:
        return None

    if kwargs.get("is_default"):
        await _clear_defaults(db)

    for field, value in kwargs.items():
        if value is not None and hasattr(instruction, field):
            setattr(instruction, field, value)

    await db.commit()
    await db.refresh(instruction)
    return instruction


async def delete_instruction(db: AsyncSession, instruction_id: int) -> bool:
    instruction = await db.get(SystemInstruction, instruction_id)
    if not instruction:
        return False
    await db.delete(instruction)
    await db.commit()
    return True


async def _clear_defaults(db: AsyncSession):
    """Clear is_default on all instructions."""
    result = await db.execute(
        select(SystemInstruction).where(SystemInstruction.is_default == True)
    )
    for inst in result.scalars().all():
        inst.is_default = False
