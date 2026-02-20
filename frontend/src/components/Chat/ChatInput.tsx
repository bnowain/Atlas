import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'

interface ChatInputProps {
  onSend: (text: string) => void
  disabled?: boolean
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 200) + 'px'
    }
  }, [text])

  return (
    <div className="border-t border-gray-800 px-4 py-3">
      <div className="flex items-end gap-2 bg-gray-800 rounded-xl px-4 py-2">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Atlas..."
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent outline-none resize-none text-sm text-gray-100 placeholder-gray-500 py-1.5 max-h-[200px]"
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || !text.trim()}
          className="p-1.5 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4 text-blue-400" />
        </button>
      </div>
      <div className="text-[11px] text-gray-600 mt-1 px-1">
        Enter to send, Shift+Enter for new line
      </div>
    </div>
  )
}
