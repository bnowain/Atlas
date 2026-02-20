"""Unified LLM client — routes to local vLLM or external API providers."""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx
from openai import AsyncOpenAI

from app.config import LLM_PROFILES, LLM_FALLBACKS

logger = logging.getLogger(__name__)

# Cache of OpenAI-compatible clients keyed by base_url
_openai_clients: dict[str, AsyncOpenAI] = {}


def _get_openai_client(base_url: str, api_key: str = "not-needed") -> AsyncOpenAI:
    """Get or create a cached AsyncOpenAI client for a given base URL."""
    cache_key = f"{base_url}:{api_key[:8]}"
    if cache_key not in _openai_clients:
        _openai_clients[cache_key] = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
    return _openai_clients[cache_key]


async def _check_local_available(profile_key: str) -> bool:
    """Check if a local vLLM backend is responding."""
    profile = LLM_PROFILES.get(profile_key)
    if not profile:
        return False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{profile.base_url}/models")
            return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


async def complete(
    profile: str | None = None,
    messages: list[dict] | None = None,
    tools: list[dict] | None = None,
    stream: bool = False,
    # External provider override
    provider_base_url: str | None = None,
    provider_api_key: str | None = None,
    provider_model: str | None = None,
    provider_type: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> dict | AsyncIterator[dict]:
    """
    Send a chat completion request.

    If provider_base_url is set, routes to external API.
    Otherwise uses local vLLM profile with fallback chain.
    """
    messages = messages or []

    # --- External provider ---
    if provider_base_url:
        return await _complete_external(
            base_url=provider_base_url,
            api_key=provider_api_key or "",
            model=provider_model or "",
            provider_type=provider_type or "openai",
            messages=messages,
            tools=tools,
            stream=stream,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    # --- Local vLLM ---
    profile_key = profile or "fast"
    return await _complete_local(
        profile_key=profile_key,
        messages=messages,
        tools=tools,
        stream=stream,
        max_tokens=max_tokens,
        temperature=temperature,
    )


async def _complete_local(
    profile_key: str,
    messages: list[dict],
    tools: list[dict] | None,
    stream: bool,
    max_tokens: int | None,
    temperature: float | None,
) -> dict | AsyncIterator[dict]:
    """Complete via local vLLM, with fallback chain."""
    # Try primary, then fallback
    attempts = [profile_key]
    if profile_key in LLM_FALLBACKS:
        attempts.append(LLM_FALLBACKS[profile_key])

    last_error = None
    for key in attempts:
        profile = LLM_PROFILES.get(key)
        if not profile:
            continue

        if not await _check_local_available(key):
            logger.info("Local backend '%s' not available, trying next...", key)
            continue

        try:
            client = _get_openai_client(profile.base_url)
            kwargs = {
                "model": profile.model,
                "messages": messages,
                "max_tokens": max_tokens or profile.max_tokens,
                "temperature": temperature if temperature is not None else profile.temperature,
                "stream": stream,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            if stream:
                return _stream_local(client, kwargs, key)
            else:
                resp = await client.chat.completions.create(**kwargs)
                return _parse_response(resp, key)

        except Exception as exc:
            logger.warning("Error with local backend '%s': %s", key, exc)
            last_error = exc

    raise ConnectionError(
        f"No local LLM backends available (tried: {attempts}). Last error: {last_error}"
    )


async def _stream_local(client: AsyncOpenAI, kwargs: dict, profile_key: str) -> AsyncIterator[dict]:
    """Stream tokens from a local vLLM backend."""
    stream = await client.chat.completions.create(**kwargs)
    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta:
            event = {"profile": profile_key}
            if delta.content:
                event["type"] = "token"
                event["content"] = delta.content
            if delta.tool_calls:
                event["type"] = "tool_call"
                event["tool_calls"] = [
                    {
                        "id": tc.id,
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in delta.tool_calls
                    if tc.function
                ]
            if chunk.choices[0].finish_reason:
                event["type"] = "done"
                event["finish_reason"] = chunk.choices[0].finish_reason
            yield event


async def _complete_external(
    base_url: str,
    api_key: str,
    model: str,
    provider_type: str,
    messages: list[dict],
    tools: list[dict] | None,
    stream: bool,
    max_tokens: int | None,
    temperature: float | None,
) -> dict | AsyncIterator[dict]:
    """Complete via external API (Claude, OpenAI, DeepSeek)."""

    if provider_type == "claude":
        return await _complete_anthropic(
            api_key=api_key,
            model=model,
            messages=messages,
            tools=tools,
            stream=stream,
            max_tokens=max_tokens or 4096,
            temperature=temperature,
        )

    # OpenAI-compatible (OpenAI, DeepSeek, etc.)
    actual_base_url = base_url or "https://api.openai.com/v1"
    client = _get_openai_client(actual_base_url, api_key)

    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens or 4096,
        "stream": stream,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    if stream:
        return _stream_external(client, kwargs, provider_type)
    else:
        resp = await client.chat.completions.create(**kwargs)
        return _parse_response(resp, provider_type)


async def _stream_external(client: AsyncOpenAI, kwargs: dict, provider_type: str) -> AsyncIterator[dict]:
    """Stream tokens from an external OpenAI-compatible API."""
    stream = await client.chat.completions.create(**kwargs)
    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta:
            event = {"provider": provider_type}
            if delta.content:
                event["type"] = "token"
                event["content"] = delta.content
            if delta.tool_calls:
                event["type"] = "tool_call"
                event["tool_calls"] = [
                    {
                        "id": tc.id,
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in delta.tool_calls
                    if tc.function
                ]
            if chunk.choices[0].finish_reason:
                event["type"] = "done"
                event["finish_reason"] = chunk.choices[0].finish_reason
            yield event


async def _complete_anthropic(
    api_key: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None,
    stream: bool,
    max_tokens: int,
    temperature: float | None,
) -> dict | AsyncIterator[dict]:
    """Complete via Anthropic's native API (not OpenAI-compatible)."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)

    # Convert OpenAI-format messages to Anthropic format
    system_msg = None
    anthropic_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        else:
            anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

    # Convert OpenAI tool format to Anthropic tool format
    anthropic_tools = None
    if tools:
        anthropic_tools = []
        for tool in tools:
            fn = tool["function"]
            anthropic_tools.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })

    kwargs = {
        "model": model,
        "messages": anthropic_messages,
        "max_tokens": max_tokens,
    }
    if system_msg:
        kwargs["system"] = system_msg
    if temperature is not None:
        kwargs["temperature"] = temperature
    if anthropic_tools:
        kwargs["tools"] = anthropic_tools

    if stream:
        return _stream_anthropic(client, kwargs)
    else:
        resp = await client.messages.create(**kwargs)
        # Convert Anthropic response to unified format
        result = {"provider": "claude", "tool_calls": []}
        content_parts = []
        for block in resp.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "tool_use":
                result["tool_calls"].append({
                    "id": block.id,
                    "function": {"name": block.name, "arguments": block.input},
                })
        result["content"] = "\n".join(content_parts) if content_parts else None
        result["finish_reason"] = resp.stop_reason
        return result


async def _stream_anthropic(client, kwargs) -> AsyncIterator[dict]:
    """Stream from Anthropic API."""
    async with client.messages.stream(**kwargs) as stream:
        async for event in stream:
            if hasattr(event, "type"):
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield {"type": "token", "content": event.delta.text, "provider": "claude"}
                elif event.type == "message_stop":
                    yield {"type": "done", "finish_reason": "end_turn", "provider": "claude"}


def _parse_response(resp, source: str) -> dict:
    """Parse an OpenAI-format completion response into a unified dict."""
    choice = resp.choices[0]
    result = {
        "source": source,
        "content": choice.message.content,
        "finish_reason": choice.finish_reason,
        "tool_calls": [],
    }
    if choice.message.tool_calls:
        for tc in choice.message.tool_calls:
            result["tool_calls"].append({
                "id": tc.id,
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            })
    return result
