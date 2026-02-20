import { useState, useEffect } from 'react'
import { ExternalLink, Loader2, Search, Lock } from 'lucide-react'
import { apiFetch } from '../api/client'

interface Thread {
  id: number
  title: string | null
  participant_count: number | null
  message_count: number | null
}

export default function MessagesPage() {
  const [threads, setThreads] = useState<Thread[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  const loadThreads = async (q?: string) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: '30' })
      if (q) params.set('query', q)
      const data = await apiFetch<any>(`/spokes/facebook_offline/api/threads?${params}`)
      setThreads(Array.isArray(data) ? data : data?.items || [])
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadThreads() }, [])

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold">Messages</h1>
          <span title="Private — local only"><Lock className="w-4 h-4 text-purple-400" /></span>
        </div>
        <a href="http://localhost:8147" target="_blank" rel="noopener noreferrer" className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1">
          Open Facebook Offline <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {/* Search */}
      <div className="flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 mb-6">
        <Search className="w-4 h-4 text-gray-500" />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && loadThreads(query)}
          placeholder="Search conversations..."
          className="flex-1 bg-transparent outline-none text-sm"
        />
      </div>

      {loading && <div className="text-center py-12"><Loader2 className="w-6 h-6 animate-spin mx-auto text-gray-500" /></div>}
      {error && <div className="text-red-400">{error}</div>}

      {!loading && (
        <div className="space-y-2">
          {threads.map(t => (
            <div key={t.id} className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-3">
              <div className="text-sm font-medium">{t.title || `Thread #${t.id}`}</div>
              <div className="text-xs text-gray-500 mt-1">
                {t.message_count != null && <span>{t.message_count} messages</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
