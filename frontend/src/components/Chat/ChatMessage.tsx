import { useState } from 'react'
import { Link } from 'react-router-dom'
import { User, Bot, ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import ToolCallIndicator from './ToolCallIndicator'
import type { ToolCallRecord } from '../../api/types'

interface Message {
  role: 'user' | 'assistant'
  content: string
  toolCalls?: ToolCallRecord[]
  isStreaming?: boolean
}

const MD_COMPONENTS = {
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="text-base font-semibold mt-3 mb-1 text-gray-100">{children}</h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="text-sm font-semibold mt-2 mb-1 text-gray-100">{children}</h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="text-sm font-semibold mt-1.5 mb-0.5 text-gray-200">{children}</h3>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="mb-1.5 last:mb-0">{children}</p>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="list-disc list-inside mb-1.5 space-y-0.5">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="list-decimal list-inside mb-1.5 space-y-0.5">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="ml-2">{children}</li>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold">{children}</strong>
  ),
  em: ({ children }: { children?: React.ReactNode }) => (
    <em className="italic">{children}</em>
  ),
  code: ({ children, className }: { children?: React.ReactNode; className?: string }) => {
    if (className?.includes('language-')) {
      return <code className="font-mono text-xs text-gray-300">{children}</code>
    }
    return <code className="font-mono text-xs bg-gray-700 px-1 py-0.5 rounded">{children}</code>
  },
  pre: ({ children }: { children?: React.ReactNode }) => (
    <pre className="bg-gray-900/80 rounded p-2 mb-1.5 overflow-x-auto text-xs">{children}</pre>
  ),
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className="border-l-2 border-gray-600 pl-2 text-gray-400 mb-1.5">{children}</blockquote>
  ),
  hr: () => <hr className="border-gray-700 my-2" />,
  a: ({ href, children }: { href?: string; children?: React.ReactNode }) => {
    if (href && /^\/meetings\//.test(href)) {
      return <Link to={href} className="text-blue-400 hover:underline">{children}</Link>
    }
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
        {children}
      </a>
    )
  },
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="overflow-x-auto mb-1.5">
      <table className="text-xs border-collapse w-full">{children}</table>
    </div>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="border border-gray-700 px-2 py-1 text-left bg-gray-800/50">{children}</th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="border border-gray-700 px-2 py-1 text-gray-400">{children}</td>
  ),
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
            {isUser ? (
              <div className="whitespace-pre-wrap">{message.content}</div>
            ) : (
              <ReactMarkdown components={MD_COMPONENTS as any}>
                {message.content}
              </ReactMarkdown>
            )}
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
