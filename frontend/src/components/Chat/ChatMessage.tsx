import { useState } from 'react'
import { User, Bot, ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import ToolCallIndicator from './ToolCallIndicator'
import type { ToolCallRecord } from '../../api/types'

interface Message {
  role: 'user' | 'assistant'
  content: string
  toolCalls?: ToolCallRecord[]
  isStreaming?: boolean
}

export default function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center shrink-0 mt-0.5">
          <Bot className="w-4 h-4 text-blue-400" />
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? 'order-first' : ''}`}>
        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-1.5 mb-2">
            {message.toolCalls.map((tc, i) => (
              <ToolCallIndicator key={i} toolCall={tc} />
            ))}
          </div>
        )}

        {/* Content */}
        {message.content && (
          <div
            className={`rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
              isUser
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-200'
            }`}
          >
            <div className="whitespace-pre-wrap">{message.content}</div>
            {message.isStreaming && (
              <span className="inline-block w-1.5 h-4 bg-blue-400 animate-pulse ml-0.5 align-text-bottom" />
            )}
          </div>
        )}

        {/* Streaming with no content yet */}
        {message.isStreaming && !message.content && !message.toolCalls?.length && (
          <div className="bg-gray-800 rounded-xl px-4 py-2.5 text-sm">
            <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center shrink-0 mt-0.5">
          <User className="w-4 h-4 text-gray-300" />
        </div>
      )}
    </div>
  )
}
