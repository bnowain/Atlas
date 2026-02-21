"""SQLAlchemy ORM models for Atlas."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, Text, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Phase 2: LLM provider management
# ---------------------------------------------------------------------------

class SystemInstruction(Base):
    __tablename__ = "system_instructions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    provider_type = Column(String, nullable=False)  # "claude", "openai", "deepseek"
    api_key_encrypted = Column(String, nullable=True)
    base_url = Column(String, nullable=True)
    model_id = Column(String, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Phase 2: Chat persistence
# ---------------------------------------------------------------------------

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=True)
    model_profile = Column(String, nullable=True)   # "fast" / "quality" / "code" or provider id
    provider_used = Column(String, nullable=True)    # "local" or provider name
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.created_at")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # "user", "assistant", "system", "tool"
    content = Column(Text, nullable=True)
    tool_calls = Column(JSON, nullable=True)
    model_profile = Column(String, nullable=True)
    provider_used = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


# ---------------------------------------------------------------------------
# Phase 4: Unified person directory
# ---------------------------------------------------------------------------

class UnifiedPerson(Base):
    __tablename__ = "unified_people"

    id = Column(Integer, primary_key=True, autoincrement=True)
    display_name = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    mappings = relationship("PersonMapping", back_populates="unified_person", cascade="all, delete-orphan")


class PersonMapping(Base):
    __tablename__ = "person_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    unified_person_id = Column(Integer, ForeignKey("unified_people.id", ondelete="CASCADE"), nullable=False)
    spoke_key = Column(String, nullable=False)       # "civic_media", "facebook_offline", etc.
    spoke_person_id = Column(String, nullable=False)  # ID in the spoke's DB
    spoke_person_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    unified_person = relationship("UnifiedPerson", back_populates="mappings")
