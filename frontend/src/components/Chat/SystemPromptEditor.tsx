import { useState, useEffect } from 'react'
import { Save, RotateCcw, Loader2 } from 'lucide-react'
import { getSystemPrompt, updateSystemPrompt } from '../../api/systemPrompt'
import { formatRelative } from '../../utils/formatters'

export default function SystemPromptEditor() {
  const [content, setContent] = useState('')
  const [original, setOriginal] = useState('')
  const [updatedAt, setUpdatedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getSystemPrompt()
      .then(data => {
        setContent(data.content)
        setOriginal(data.content)
        setUpdatedAt(data.updated_at)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const isDirty = content !== original

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      const data = await updateSystemPrompt(content)
      setOriginal(data.content)
      setContent(data.content)
      setUpdatedAt(data.updated_at)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  function handleReset() {
    setContent(original)
  }

  if (loading) {
    return (
      <div className="border-b border-gray-800 px-4 py-3 flex items-center gap-2 text-gray-500 text-xs">
        <Loader2 className="w-3 h-3 animate-spin" />
        Loading system prompt…
      </div>
    )
  }

  return (
    <div className="border-b border-gray-800 bg-gray-900/60">
      <div className="px-4 py-2">
        <textarea
          className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs font-mono text-gray-200 resize-none focus:outline-none focus:border-blue-500/50 transition-colors"
          rows={12}
          value={content}
          onChange={e => setContent(e.target.value)}
          spellCheck={false}
          placeholder="Enter base system prompt…"
        />
        {error && (
          <div className="text-red-400 text-xs mt-1">{error}</div>
        )}
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-gray-600">
            {updatedAt ? `Last saved: ${formatRelative(updatedAt)}` : 'Not yet saved'}
            {isDirty && <span className="text-yellow-500 ml-2">Unsaved changes</span>}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleReset}
              disabled={!isDirty || saving}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-gray-700 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
            <button
              onClick={handleSave}
              disabled={!isDirty || saving}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
