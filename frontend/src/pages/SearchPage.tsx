import { useState } from 'react'
import { Search, Loader2 } from 'lucide-react'
import { useDebounce } from '../hooks/useDebounce'
import { spokeLabel, spokeColor, spokeBg, formatDate } from '../utils/formatters'
import { apiFetch } from '../api/client'
import type { SearchResult } from '../api/types'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const data = await apiFetch<{ results: SearchResult[] }>(`/search?q=${encodeURIComponent(query)}&limit=30`)
      setResults(data.results)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-3 md:px-6 py-4 md:py-8">
      <h1 className="text-xl font-semibold mb-6">Unified Search</h1>

      {/* Search input */}
      <div className="flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 mb-6">
        <Search className="w-4 h-4 text-gray-500" />
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder="Search across all apps..."
          className="flex-1 bg-transparent outline-none text-sm"
        />
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-3 py-1 rounded-lg transition-colors"
        >
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Search'}
        </button>
      </div>

      {/* Results */}
      {loading && (
        <div className="text-center text-gray-500 py-12">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
          Searching...
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="text-center text-gray-500 py-12">No results found</div>
      )}

      <div className="space-y-3">
        {results.map((r, i) => (
          <div key={i} className={`border rounded-xl p-4 ${spokeBg(r.source)}`}>
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs font-medium ${spokeColor(r.source)}`}>
                {spokeLabel(r.source)}
              </span>
              <span className="text-xs text-gray-600">&middot;</span>
              <span className="text-xs text-gray-500">{r.type}</span>
              {r.date && (
                <>
                  <span className="text-xs text-gray-600">&middot;</span>
                  <span className="text-xs text-gray-500">{formatDate(r.date)}</span>
                </>
              )}
            </div>
            <div className="text-sm font-medium">{r.title}</div>
            {r.snippet && (
              <div className="text-xs text-gray-400 mt-1 line-clamp-2">{r.snippet}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
