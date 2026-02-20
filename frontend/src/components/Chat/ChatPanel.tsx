import { useRef, useEffect } from 'react'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import type { ToolCallRecord } from '../../api/types'

interface Message {
  role: 'user' | 'assistant'
  content: string
  toolCalls?: ToolCallRecord[]
  isStreaming?: boolean
}

interface ChatPanelProps {
  messages: Message[]
  isStreaming: boolean
  error: string | null
  onSend: (text: string) => void
}

export default function ChatPanel({ messages, isStreaming, error, onSend }: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-1">Ask Atlas anything</p>
              <p className="text-sm">Query meetings, articles, archives, and messages</p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-400 text-sm">
            {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={onSend} disabled={isStreaming} />
    </div>
  )
}
