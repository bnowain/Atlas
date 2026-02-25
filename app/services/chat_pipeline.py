"""Core chat orchestration — classify → LLM → tool calls → stream response."""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Conversation, ConversationMessage
from app.services import llm_client, provider_manager, instruction_manager, system_prompt_manager
from app.services.query_classifier import classify
from app.services.schema_context import get_schema_context
from app.services.tool_executor import execute_tool_call

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Atlas, a civic accountability research assistant for Redding and Shasta County, CA.
You have access to tools that query local databases of:
- Meeting transcripts with speaker identification (civic_media)
- Structured vote records parsed from meeting minutes — who voted how on what (civic_media)
- The Brown Act (CA open meetings law) stored section-by-section for lookup (civic_media)
- News articles from 45+ local and national sources (article_tracker)
- An archive of civic media files (Shasta-DB)
- Personal Facebook messages and posts (facebook_offline — treat as private)
- Public records requests from Shasta County (shasta_pra)
- Monitored public Facebook page posts and comments (facebook_monitor)
- Campaign finance disclosures — filers, filings, transactions, elections (campaign_finance)

## Tool use rules
- **Chain tools without stopping.** If a tool returns an ID or partial result needed by another tool, call that next tool immediately — do NOT stop and ask the user if they want more information.
- **Complete multi-step queries autonomously.** A question like "tell me about X and their meetings" requires multiple tool calls. Execute all of them, then present the final answer.
- **Never surface raw IDs as the answer.** A person_id, meeting_id, or filer_id is an intermediate step, not a result. Always resolve it with the appropriate follow-up tool.
- Cite sources with dates/titles. Keep final responses concise.
- When showing vote data, include outcome, tally, mover/seconder, and any dissenting votes by name.
- If a tool returns no results, say so — don't make up data."""

SYSTEM_PROMPT_CHAT_ONLY = """You are Atlas, a helpful general-purpose assistant. Answer questions directly from your knowledge. Be concise and accurate."""

MAX_TOOL_ROUNDS = 5


async def chat(
    db: AsyncSession,
    message: str,
    conversation_id: int | None = None,
    profile: str | None = None,
    provider_id: int | None = None,
    spokes: list[str] | None = None,
    instruction_id: int | None = None,
) -> AsyncIterator[dict]:
    """
    Process a chat message, yielding SSE events.

    Event types: token, tool_call, tool_result, done, error
    """

    # Load or create conversation
    if conversation_id:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            yield {"type": "error", "content": f"Conversation {conversation_id} not found"}
            return
    else:
        conversation = Conversation(title=message[:100])
        db.add(conversation)
        await db.flush()

    # Save user message
    user_msg = ConversationMessage(
        conversation_id=conversation.id,
        role="user",
        content=message,
    )
    db.add(user_msg)
    await db.flush()

    # Yield conversation ID for the frontend
    yield {"type": "conversation_id", "id": conversation.id}

    # Classify the query
    classification = classify(message, allowed_spokes=spokes)
    effective_profile = profile or classification.profile

    # Resolve provider (external override or local)
    provider_kwargs = {}
    provider_label = f"local:{effective_profile}"

    if provider_id:
        provider = await provider_manager.get_provider(db, provider_id)
        if provider and provider.enabled:
            api_key = ""
            if provider.api_key_encrypted:
                api_key = provider_manager.decrypt_key(provider.api_key_encrypted)
            provider_kwargs = {
                "provider_base_url": provider.base_url,
                "provider_api_key": api_key,
                "provider_model": provider.model_id,
                "provider_type": provider.provider_type,
            }
            provider_label = provider.name
    else:
        # Check for default external provider
        default_provider = await provider_manager.get_default_provider(db)
        if default_provider:
            api_key = ""
            if default_provider.api_key_encrypted:
                api_key = provider_manager.decrypt_key(default_provider.api_key_encrypted)
            provider_kwargs = {
                "provider_base_url": default_provider.base_url,
                "provider_api_key": api_key,
                "provider_model": default_provider.model_id,
                "provider_type": default_provider.provider_type,
            }
            provider_label = default_provider.name

    # Update conversation metadata
    conversation.model_profile = effective_profile
    conversation.provider_used = provider_label

    # Build messages for LLM — use chat-only prompt when no tools
    if classification.tools:
        stored = await system_prompt_manager.get_system_prompt(db)
        system_prompt = stored.content if stored else SYSTEM_PROMPT
    else:
        system_prompt = SYSTEM_PROMPT_CHAT_ONLY

    # Inject per-spoke schema context so the LLM knows field names, enum values,
    # key formats, and cross-spoke research patterns for the matched spokes
    schema_ctx = get_schema_context(classification.spokes)
    if schema_ctx:
        system_prompt += "\n\n" + schema_ctx

    # Append custom instruction if selected
    if instruction_id:
        instruction = await instruction_manager.get_instruction(db, instruction_id)
        if instruction:
            system_prompt += f"\n\n## Custom Instructions\n{instruction.content}"

    llm_messages = [{"role": "system", "content": system_prompt}]

    # Load conversation history (last 20 messages for context).
    # Always append the current user message explicitly so it's guaranteed to be
    # last, regardless of whether SQLAlchemy's ORM collection tracking includes
    # the just-flushed user_msg in conversation.messages (it may not, depending
    # on how the FK was set vs. the relationship attribute).
    if conversation_id:
        existing_msgs = list(conversation.messages)
        # Exclude user_msg from history to avoid duplication (it's added below)
        history = [m for m in existing_msgs if m.id != user_msg.id]
        for msg in history[-20:]:
            llm_messages.append({"role": msg.role, "content": msg.content or ""})

    # Current user message always last
    llm_messages.append({"role": "user", "content": message})

    # Tool call loop (streaming)
    full_response = ""
    all_tool_calls = []

    for round_num in range(MAX_TOOL_ROUNDS):
        # Consume stream: yield tokens immediately, collect tool calls
        round_content = ""
        tool_calls = []

        try:
            if provider_kwargs:
                stream = await llm_client.complete(
                    messages=llm_messages,
                    tools=classification.tools,
                    stream=True,
                    **provider_kwargs,
                )
            else:
                stream = await llm_client.complete(
                    profile=effective_profile,
                    messages=llm_messages,
                    tools=classification.tools,
                    stream=True,
                )

            async for event in stream:
                etype = event.get("type")
                if etype == "token":
                    round_content += event["content"]
                    full_response += event["content"]
                    yield {"type": "token", "content": event["content"]}
                elif etype == "tool_calls_complete":
                    tool_calls = event["tool_calls"]
                elif etype == "done":
                    break

        except Exception as exc:
            logger.exception("LLM error in round %d", round_num)
            yield {"type": "error", "content": f"LLM error: {exc}"}
            return

        if not tool_calls:
            break

        # Execute tool calls
        tool_messages = []
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            fn_args = tc["function"]["arguments"]
            if isinstance(fn_args, str):
                try:
                    fn_args = json.loads(fn_args)
                except json.JSONDecodeError:
                    fn_args = {}

            yield {"type": "tool_call", "name": fn_name, "arguments": fn_args}

            tool_result = await execute_tool_call(fn_name, fn_args)
            all_tool_calls.append({
                "name": fn_name,
                "arguments": fn_args,
                "result": tool_result,
            })

            yield {"type": "tool_result", "name": fn_name, "result": tool_result}

            tool_messages.append({
                "role": "tool",
                "content": json.dumps(tool_result, default=str),
                "tool_call_id": tc.get("id", fn_name),
            })

        # Add the assistant's response with tool calls to messages for next round
        assistant_msg = {"role": "assistant", "content": round_content or ""}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.get("id", tc["function"]["name"]),
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"] if isinstance(tc["function"]["arguments"], str) else json.dumps(tc["function"]["arguments"]),
                    },
                }
                for tc in tool_calls
            ]
        llm_messages.append(assistant_msg)
        llm_messages.extend(tool_messages)

    # Save assistant response
    assistant_msg = ConversationMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=full_response,
        tool_calls=all_tool_calls if all_tool_calls else None,
        model_profile=effective_profile,
        provider_used=provider_label,
    )
    db.add(assistant_msg)
    await db.commit()

    yield {"type": "done", "conversation_id": conversation.id}
