import { MessageSquare } from 'lucide-react'
import ChatPanel from '../Chat/ChatPanel'
import { useChat } from '../../hooks/useChat'

interface ResultsChatProps {
  query: string
  spokes: string[]
}

export default function ResultsChat({ query, spokes }: ResultsChatProps) {
  const chat = useChat()

  return (
    <div className="flex flex-col h-full border-l border-gray-800">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-800 shrink-0">
        <MessageSquare className="w-3.5 h-3.5 text-gray-500" />
        <span className="text-xs font-medium text-gray-400">Chat about these results</span>
      </div>
      <div className="flex-1 min-h-0">
        <ChatPanel
          messages={chat.messages}
          isStreaming={chat.isStreaming}
          error={chat.error}
          onSend={text => chat.sendMessage(text, undefined, undefined, spokes.length > 0 ? spokes : null)}
        />
      </div>
    </div>
  )
}
