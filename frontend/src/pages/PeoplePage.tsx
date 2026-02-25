import { useState, useEffect, useCallback } from 'react'
import { Loader2, Users, RefreshCw, Search } from 'lucide-react'
import { apiFetch } from '../api/client'
import { spokeLabel, spokeColor } from '../utils/formatters'
import type { UnifiedPerson } from '../api/types'

interface SyncResult {
  spoke_key: string
  total_fetched: number
  created: number
  updated: number
  unchanged: number
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export default function PeoplePage() {
  const [people, setPeople] = useState<UnifiedPerson[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)

  const debouncedSearch = useDebounce(search, 300)

  const loadPeople = useCallback((q?: string) => {
    setLoading(true)
    const url = q ? `/people?q=${encodeURIComponent(q)}` : '/people'
    apiFetch<UnifiedPerson[]>(url)
      .then(setPeople)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadPeople(debouncedSearch || undefined)
  }, [debouncedSearch, loadPeople])

  const handleSync = async () => {
    setSyncing(true)
    setSyncResult(null)
    setSyncError(null)
    try {
      const result = await apiFetch<SyncResult>('/people/sync/civic_media', { method: 'POST' })
      setSyncResult(result)
      loadPeople(debouncedSearch || undefined)
    } catch (e: unknown) {
      setSyncError(e instanceof Error ? e.message : 'Sync failed')
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-3 md:px-6 py-4 md:py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-gray-400" />
          <h1 className="text-xl font-semibold">People</h1>
          {!loading && (
            <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
              {people.length}
            </span>
          )}
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {syncing ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          Sync from civic_media
        </button>
      </div>

      {syncResult && (
        <div className="mb-4 px-4 py-3 bg-green-900/30 border border-green-700/40 rounded-xl text-sm text-green-300">
          Sync complete — fetched {syncResult.total_fetched}, created {syncResult.created}, updated {syncResult.updated}, unchanged {syncResult.unchanged}
        </div>
      )}

      {syncError && (
        <div className="mb-4 px-4 py-3 bg-red-900/30 border border-red-700/40 rounded-xl text-sm text-red-300">
          {syncError}
        </div>
      )}

      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search people…"
          className="w-full pl-9 pr-4 py-2 text-sm bg-gray-800 border border-gray-700 rounded-xl focus:outline-none focus:border-blue-500 placeholder-gray-600"
        />
      </div>

      {error && <div className="text-red-400 mb-4 text-sm">{error}</div>}

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-6 h-6 animate-spin text-gray-500" />
        </div>
      ) : people.length === 0 ? (
        <div className="text-gray-500 text-sm">
          {search
            ? `No people match "${search}".`
            : 'No unified people records yet. Click "Sync from civic_media" to import speakers.'}
        </div>
      ) : (
        <div className="space-y-3">
          {people.map(p => (
            <div key={p.id} className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-3">
              <div className="text-sm font-medium">{p.display_name}</div>
              {p.notes && <div className="text-xs text-gray-500 mt-0.5">{p.notes}</div>}
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                {p.mappings.map(m => (
                  <span key={m.id} className={`text-xs px-2 py-0.5 rounded-full bg-gray-700 ${spokeColor(m.spoke_key)}`}>
                    {spokeLabel(m.spoke_key)}: {m.spoke_person_name || m.spoke_person_id}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
