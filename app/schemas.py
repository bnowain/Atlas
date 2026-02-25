"""Pydantic models for Atlas API request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Spoke health
# ---------------------------------------------------------------------------

class SpokeStatus(BaseModel):
    key: str
    name: str
    base_url: str
    online: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class TailscaleInfo(BaseModel):
    ip: Optional[str] = None
    hostname: Optional[str] = None
    url: Optional[str] = None


class HealthResponse(BaseModel):
    status: str  # "ok"
    spokes: list[SpokeStatus]
    tailscale: Optional[TailscaleInfo] = None


# ---------------------------------------------------------------------------
# LLM providers
# ---------------------------------------------------------------------------

class LLMProviderCreate(BaseModel):
    name: str
    provider_type: str  # "claude", "openai", "deepseek"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_id: str
    enabled: bool = True
    is_default: bool = False


class LLMProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_id: Optional[str] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None


class LLMProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider_type: str
    base_url: Optional[str]
    model_id: str
    enabled: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    # api_key intentionally excluded


# ---------------------------------------------------------------------------
# System Instructions
# ---------------------------------------------------------------------------

class SystemInstructionCreate(BaseModel):
    name: str
    content: str
    is_default: bool = False


class SystemInstructionUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    is_default: Optional[bool] = None


class SystemInstructionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    content: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    profile: Optional[str] = None      # "fast", "quality", "code"
    provider_id: Optional[int] = None   # external provider override
    spokes: Optional[list[str]] = None  # None = all, [] = chat only
    instruction_id: Optional[int] = None  # custom instruction preset


class ConversationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: Optional[str]
    tool_calls: Optional[list | dict] = None
    model_profile: Optional[str]
    provider_used: Optional[str]
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: Optional[str]
    model_profile: Optional[str]
    provider_used: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageResponse] = []


class ConversationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: Optional[str]
    model_profile: Optional[str]
    provider_used: Optional[str]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Unified search
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    q: str
    sources: Optional[list[str]] = None  # spoke keys to search
    limit: int = 20


class SearchResult(BaseModel):
    source: str  # spoke key
    type: str    # "meeting", "article", "file", "message", "post"
    title: str
    snippet: Optional[str] = None
    url: Optional[str] = None
    date: Optional[datetime] = None
    metadata: Optional[dict] = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int


# ---------------------------------------------------------------------------
# Unified people
# ---------------------------------------------------------------------------

class PersonMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    spoke_key: str
    spoke_person_id: str
    spoke_person_name: Optional[str]


class UnifiedPersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    notes: Optional[str]
    created_at: datetime
    mappings: list[PersonMappingResponse] = []


class PersonLinkRequest(BaseModel):
    spoke_key: str
    spoke_person_id: str
    spoke_person_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Base system prompt
# ---------------------------------------------------------------------------

class BaseSystemPromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    updated_at: datetime


class BaseSystemPromptUpdate(BaseModel):
    content: str
