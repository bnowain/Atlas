"""Custom system instruction preset endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SystemInstructionCreate, SystemInstructionUpdate, SystemInstructionResponse
from app.services import instruction_manager

router = APIRouter(prefix="/api/instructions", tags=["instructions"])


@router.get("", response_model=list[SystemInstructionResponse])
async def list_instructions(db: AsyncSession = Depends(get_db)):
    return await instruction_manager.list_instructions(db)


@router.post("", response_model=SystemInstructionResponse, status_code=201)
async def create_instruction(req: SystemInstructionCreate, db: AsyncSession = Depends(get_db)):
    return await instruction_manager.create_instruction(
        db,
        name=req.name,
        content=req.content,
        is_default=req.is_default,
    )


@router.get("/default", response_model=SystemInstructionResponse | None)
async def get_default_instruction(db: AsyncSession = Depends(get_db)):
    return await instruction_manager.get_default_instruction(db)


@router.patch("/{instruction_id}", response_model=SystemInstructionResponse)
async def update_instruction(
    instruction_id: int,
    req: SystemInstructionUpdate,
    db: AsyncSession = Depends(get_db),
):
    instruction = await instruction_manager.update_instruction(
        db, instruction_id, **req.model_dump(exclude_none=True)
    )
    if not instruction:
        raise HTTPException(404, "Instruction not found")
    return instruction


@router.delete("/{instruction_id}")
async def delete_instruction(instruction_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await instruction_manager.delete_instruction(db, instruction_id)
    if not deleted:
        raise HTTPException(404, "Instruction not found")
    return {"status": "deleted"}
