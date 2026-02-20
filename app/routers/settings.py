"""Settings endpoints — external LLM provider management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import LLMProviderCreate, LLMProviderUpdate, LLMProviderResponse
from app.services import provider_manager

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/providers", response_model=list[LLMProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_db)):
    return await provider_manager.list_providers(db)


@router.post("/providers", response_model=LLMProviderResponse, status_code=201)
async def create_provider(req: LLMProviderCreate, db: AsyncSession = Depends(get_db)):
    return await provider_manager.create_provider(
        db,
        name=req.name,
        provider_type=req.provider_type,
        model_id=req.model_id,
        api_key=req.api_key,
        base_url=req.base_url,
        enabled=req.enabled,
        is_default=req.is_default,
    )


@router.get("/providers/active", response_model=LLMProviderResponse | None)
async def get_active_provider(db: AsyncSession = Depends(get_db)):
    return await provider_manager.get_active_provider(db)


@router.get("/providers/{provider_id}", response_model=LLMProviderResponse)
async def get_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    provider = await provider_manager.get_provider(db, provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")
    return provider


@router.patch("/providers/{provider_id}", response_model=LLMProviderResponse)
async def update_provider(
    provider_id: int,
    req: LLMProviderUpdate,
    db: AsyncSession = Depends(get_db),
):
    provider = await provider_manager.update_provider(
        db, provider_id, **req.model_dump(exclude_none=True)
    )
    if not provider:
        raise HTTPException(404, "Provider not found")
    return provider


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await provider_manager.delete_provider(db, provider_id)
    if not deleted:
        raise HTTPException(404, "Provider not found")
    return {"status": "deleted"}


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    result = await provider_manager.test_provider(db, provider_id)
    return result
