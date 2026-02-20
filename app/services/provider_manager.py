"""CRUD for external LLM providers — API keys encrypted at rest with Fernet."""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_fernet_key
from app.models import LLMProvider

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_fernet_key())
    return _fernet


def encrypt_key(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_key(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


async def list_providers(db: AsyncSession) -> list[LLMProvider]:
    result = await db.execute(select(LLMProvider).order_by(LLMProvider.name))
    return list(result.scalars().all())


async def get_provider(db: AsyncSession, provider_id: int) -> LLMProvider | None:
    return await db.get(LLMProvider, provider_id)


async def create_provider(
    db: AsyncSession,
    name: str,
    provider_type: str,
    model_id: str,
    api_key: str | None = None,
    base_url: str | None = None,
    enabled: bool = True,
    is_default: bool = False,
) -> LLMProvider:
    if is_default:
        await _clear_defaults(db)

    provider = LLMProvider(
        name=name,
        provider_type=provider_type,
        model_id=model_id,
        api_key_encrypted=encrypt_key(api_key) if api_key else None,
        base_url=base_url,
        enabled=enabled,
        is_default=is_default,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


async def update_provider(
    db: AsyncSession,
    provider_id: int,
    **kwargs,
) -> LLMProvider | None:
    provider = await db.get(LLMProvider, provider_id)
    if not provider:
        return None

    if "api_key" in kwargs:
        key = kwargs.pop("api_key")
        if key is not None:
            provider.api_key_encrypted = encrypt_key(key)

    if kwargs.get("is_default"):
        await _clear_defaults(db)

    for field, value in kwargs.items():
        if value is not None and hasattr(provider, field):
            setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    return provider


async def delete_provider(db: AsyncSession, provider_id: int) -> bool:
    provider = await db.get(LLMProvider, provider_id)
    if not provider:
        return False
    await db.delete(provider)
    await db.commit()
    return True


async def get_default_provider(db: AsyncSession) -> LLMProvider | None:
    result = await db.execute(
        select(LLMProvider).where(LLMProvider.is_default == True, LLMProvider.enabled == True)
    )
    return result.scalar_one_or_none()


async def get_active_provider(db: AsyncSession) -> LLMProvider | None:
    """Get the active provider — default if set, otherwise first enabled."""
    default = await get_default_provider(db)
    if default:
        return default
    result = await db.execute(
        select(LLMProvider).where(LLMProvider.enabled == True).order_by(LLMProvider.id).limit(1)
    )
    return result.scalar_one_or_none()


async def _clear_defaults(db: AsyncSession):
    """Clear is_default on all providers."""
    result = await db.execute(select(LLMProvider).where(LLMProvider.is_default == True))
    for p in result.scalars().all():
        p.is_default = False


async def test_provider(db: AsyncSession, provider_id: int) -> dict:
    """Test connection to an external provider."""
    provider = await db.get(LLMProvider, provider_id)
    if not provider:
        return {"success": False, "error": "Provider not found"}

    api_key = decrypt_key(provider.api_key_encrypted) if provider.api_key_encrypted else ""

    try:
        from app.services.llm_client import complete

        result = await complete(
            provider_base_url=provider.base_url,
            provider_api_key=api_key,
            provider_model=provider.model_id,
            provider_type=provider.provider_type,
            messages=[{"role": "user", "content": "Say 'ok'"}],
            max_tokens=5,
            temperature=0,
        )
        return {"success": True, "response": result.get("content", "")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
