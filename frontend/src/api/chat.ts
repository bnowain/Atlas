import type { ChatRequest, ChatSSEEvent, Conversation, ConversationListItem } from './types'
import { apiFetch, apiDelete } from './client'

export async function* streamChat(req: ChatRequest): AsyncGenerator<ChatSSEEvent> {
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })

  if (!resp.ok) {
    throw new Error(`Chat error: ${resp.status}`)
  }

  const reader = resp.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event: ChatSSEEvent = JSON.parse(line.slice(6))
          yield event
        } catch {
          // skip malformed events
        }
      }
    }
  }
}

export function listConversations(limit = 50): Promise<ConversationListItem[]> {
  return apiFetch(`/chat/conversations?limit=${limit}`)
}

export function getConversation(id: number): Promise<Conversation> {
  return apiFetch(`/chat/conversations/${id}`)
}

export function deleteConversation(id: number): Promise<void> {
  return apiDelete(`/chat/conversations/${id}`)
}
