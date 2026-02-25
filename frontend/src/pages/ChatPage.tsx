import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Plus, History, Trash2, Terminal } from 'lucide-react'
import ChatPanel from '../components/Chat/ChatPanel'
import ModelSelector from '../components/Chat/ModelSelector'
import InstructionSelector from '../components/Chat/InstructionSelector'
import SpokeFilter, { ALL_SPOKE_KEYS } from '../components/Chat/SpokeFilter'
import SystemPromptEditor from '../components/Chat/SystemPromptEditor'
import { useChat } from '../hooks/useChat'
import { listConversations, getConversation, deleteConversation } from '../api/chat'
import { getDefaultInstruction } from '../api/instructions'
import type { ConversationListItem } from '../api/types'
import { formatRelative } from '../utils/formatters'

export default function ChatPage() {
  const { conversationId: urlId } = useParams()
  const navigate = useNavigate()
  const chat = useChat()
  const [conversations, setConversations] = useState<ConversationListItem[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [showSystemPrompt, setShowSystemPrompt] = useState(false)
  const [selectedProfile, setSelectedProfile] = useState<string | null>(null)
  const [selectedProviderId, setSelectedProviderId] = useState<number | null>(null)
  const [activeSpokes, setActiveSpokes] = useState<string[]>([...ALL_SPOKE_KEYS])
  const [selectedInstructionId, setSelectedInstructionId] = useState<number | null>(null)

  // Load default instruction on mount
  useEffect(() => {
    getDefaultInstruction().then(inst => {
      if (inst) setSelectedInstructionId(inst.id)
    }).catch(() => {})
  }, [])

  // Load conversation list
  useEffect(() => {
    listConversations(30).then(setConversations).catch(() => {})
  }, [chat.conversationId])

  // Load conversation from URL
  useEffect(() => {
    if (urlId) {
      const id = parseInt(urlId)
      if (!isNaN(id) && id !== chat.conversationId) {
        getConversation(id).then(conv => {
          chat.setConversationId(conv.id)
          chat.setMessages(
            conv.messages
              .filter(m => m.role === 'user' || m.role === 'assistant')
              .map(m => ({
                role: m.role as 'user' | 'assistant',
                content: m.content || '',
                toolCalls: m.tool_calls || undefined,
              }))
          )
        }).catch(() => navigate('/chat'))
      }
    }
  }, [urlId])

  // Sync URL with conversation ID
  useEffect(() => {
    if (chat.conversationId && !urlId) {
      navigate(`/chat/${chat.conversationId}`, { replace: true })
    }
  }, [chat.conversationId])

  const handleNewChat = () => {
    chat.setConversationId(null)
    chat.setMessages([])
    navigate('/chat')
  }

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    await deleteConversation(id)
    setConversations(prev => prev.filter(c => c.id !== id))
    if (chat.conversationId === id) handleNewChat()
  }

  return (
    <div className="flex h-full relative">
      {/* History sidebar — overlay on mobile, inline on desktop */}
      {showHistory && (
        <>
          <div className="fixed inset-0 bg-black/50 z-20 md:hidden" onClick={() => setShowHistory(false)} />
          <div className="fixed inset-y-0 left-0 z-30 w-64 md:static md:z-auto border-r border-gray-800 flex flex-col bg-gray-900/95 md:bg-gray-900/50">
          <div className="flex items-center justify-between px-3 py-3 border-b border-gray-800">
            <span className="text-sm font-medium">History</span>
            <button
              onClick={handleNewChat}
              className="p-1 hover:bg-gray-700 rounded transition-colors"
              title="New chat"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {conversations.map(conv => (
              <button
                key={conv.id}
                onClick={() => navigate(`/chat/${conv.id}`)}
                className={`w-full text-left px-3 py-2.5 border-b border-gray-800/50 hover:bg-gray-800/50 transition-colors group ${
                  chat.conversationId === conv.id ? 'bg-gray-800' : ''
                }`}
              >
                <div className="text-xs text-gray-300 truncate">{conv.title || 'Untitled'}</div>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-[11px] text-gray-500">{formatRelative(conv.created_at)}</span>
                  <button
                    onClick={e => handleDelete(conv.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-400 transition-all"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </button>
            ))}
          </div>
        </div>
        </>
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex flex-wrap items-center gap-2 px-2 md:px-4 py-2 border-b border-gray-800">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className={`p-1.5 rounded-lg transition-colors ${showHistory ? 'bg-gray-700' : 'hover:bg-gray-800'}`}
            title="Toggle history"
          >
            <History className="w-4 h-4" />
          </button>
          <button
            onClick={handleNewChat}
            className="p-1.5 rounded-lg hover:bg-gray-800 transition-colors"
            title="New chat"
          >
            <Plus className="w-4 h-4" />
          </button>
          <ModelSelector
            selectedProfile={selectedProfile}
            selectedProviderId={selectedProviderId}
            onSelectLocal={(profile) => { setSelectedProfile(profile); setSelectedProviderId(null) }}
            onSelectProvider={(id) => { setSelectedProviderId(id); setSelectedProfile(null) }}
            onProviderCreated={() => {}}
          />
          <SpokeFilter activeSpokes={activeSpokes} onChange={setActiveSpokes} />
          <InstructionSelector
            selectedInstructionId={selectedInstructionId}
            onSelect={setSelectedInstructionId}
          />
          <button
            onClick={() => setShowSystemPrompt(!showSystemPrompt)}
            className={`p-1.5 rounded-lg transition-colors ml-auto ${showSystemPrompt ? 'bg-gray-700 text-blue-400' : 'hover:bg-gray-800 text-gray-500'}`}
            title="Edit base system prompt"
          >
            <Terminal className="w-4 h-4" />
          </button>
          <span className="text-sm text-gray-500">
            {chat.conversationId ? `Chat #${chat.conversationId}` : 'New conversation'}
          </span>
        </div>

        {showSystemPrompt && <SystemPromptEditor />}

        <ChatPanel
          messages={chat.messages}
          isStreaming={chat.isStreaming}
          error={chat.error}
          onSend={text => chat.sendMessage(text, selectedProfile || undefined, selectedProviderId || undefined, activeSpokes, selectedInstructionId)}
        />
      </div>
    </div>
  )
}
