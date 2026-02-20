"""Chat endpoints — SSE streaming, conversation CRUD."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models import Conversation, ConversationMessage
from app.schemas import (
    ChatRequest, ConversationResponse, ConversationListItem,
)
from app.services.chat_pipeline import chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def send_message(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Send a chat message and stream the response via SSE."""

    async def event_generator():
        async for event in chat(
            db=db,
            message=req.message,
            conversation_id=req.conversation_id,
            profile=req.profile,
            provider_id=req.provider_id,
        ):
            yield {"event": event.get("type", "message"), "data": json.dumps(event, default=str)}

    return EventSourceResponse(event_generator())


@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List recent conversations."""
    result = await db.execute(
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    """Get a conversation with all messages."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        from fastapi import HTTPException
        raise HTTPException(404, "Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a conversation and all its messages."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        from fastapi import HTTPException
        raise HTTPException(404, "Conversation not found")
    await db.delete(conversation)
    await db.commit()
    return {"status": "deleted"}
