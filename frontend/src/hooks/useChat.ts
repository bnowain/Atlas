import { useState, useCallback, useRef } from 'react'
import { streamChat } from '../api/chat'
import type { ChatSSEEvent, ToolCallRecord } from '../api/types'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  toolCalls?: ToolCallRecord[]
  isStreaming?: boolean
}

interface UseChatReturn {
  messages: ChatMessage[]
  isStreaming: boolean
  conversationId: number | null
  error: string | null
  sendMessage: (text: string, profile?: string, providerId?: number, spokes?: string[] | null, instructionId?: number | null) => Promise<void>
  setConversationId: (id: number | null) => void
  setMessages: (msgs: ChatMessage[]) => void
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const activeToolCalls = useRef<ToolCallRecord[]>([])

  const sendMessage = useCallback(async (text: string, profile?: string, providerId?: number, spokes?: string[] | null, instructionId?: number | null) => {
    setError(null)
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setIsStreaming(true)
    activeToolCalls.current = []

    // Add a streaming placeholder for assistant
    setMessages(prev => [...prev, { role: 'assistant', content: '', isStreaming: true }])

    try {
      const stream = streamChat({
        message: text,
        conversation_id: conversationId,
        profile: profile || null,
        provider_id: providerId || null,
        spokes: spokes !== undefined ? spokes : null,
        instruction_id: instructionId ?? null,
      })

      let fullContent = ''

      for await (const event of stream) {
        switch (event.type) {
          case 'conversation_id':
            if (event.id) setConversationId(event.id)
            break

          case 'token':
            fullContent += event.content || ''
            setMessages(prev => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = { ...last, content: fullContent, isStreaming: true }
              }
              return updated
            })
            break

          case 'tool_call':
            activeToolCalls.current.push({
              name: event.name || '',
              arguments: event.arguments || {},
              result: { success: false },
            })
            setMessages(prev => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = { ...last, toolCalls: [...activeToolCalls.current] }
              }
              return updated
            })
            break

          case 'tool_result':
            // Update the last tool call with the result
            const idx = activeToolCalls.current.findIndex(tc => tc.name === event.name)
            if (idx >= 0 && event.result) {
              activeToolCalls.current[idx] = { ...activeToolCalls.current[idx], result: event.result }
            }
            setMessages(prev => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = { ...last, toolCalls: [...activeToolCalls.current] }
              }
              return updated
            })
            break

          case 'done':
            setMessages(prev => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = { ...last, content: fullContent, isStreaming: false, toolCalls: activeToolCalls.current.length ? [...activeToolCalls.current] : undefined }
              }
              return updated
            })
            break

          case 'error':
            setError(event.content || 'Unknown error')
            break
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Stream error')
    } finally {
      setIsStreaming(false)
      // Ensure any accumulated content is committed even if `done` was never received
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last?.role === 'assistant' && last.isStreaming) {
          updated[updated.length - 1] = {
            ...last,
            content: fullContent || last.content,
            isStreaming: false,
          }
        }
        return updated
      })
    }
  }, [conversationId])

  return { messages, isStreaming, conversationId, error, sendMessage, setConversationId, setMessages }
}
