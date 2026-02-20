import { useState, useEffect } from 'react'
import { ExternalLink, Loader2, Search } from 'lucide-react'
import { apiFetch } from '../api/client'

interface ArchiveFile {
  id: number
  title: string | null
  kind: string | null
  ext: string | null
  path: string | null
}

export default function MediaBrowserPage() {
  const [files, setFiles] = useState<ArchiveFile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  const doSearch = async (q?: string) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: '50' })
      if (q) params.set('q', q)
      const data = await apiFetch<ArchiveFile[]>(`/spokes/shasta_db/search?${params}`)
      setFiles(Array.isArray(data) ? data : [])
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { doSearch() }, [])

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Archive Files</h1>
        <a href="http://localhost:8844/ui" target="_blank" rel="noopener noreferrer" className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1">
          Open Shasta-DB <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {/* Search */}
      <div className="flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 mb-6">
        <Search className="w-4 h-4 text-gray-500" />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doSearch(query)}
          placeholder="Search archive..."
          className="flex-1 bg-transparent outline-none text-sm"
        />
      </div>

      {loading && <div className="text-center py-12"><Loader2 className="w-6 h-6 animate-spin mx-auto text-gray-500" /></div>}
      {error && <div className="text-red-400">{error}</div>}

      {!loading && (
        <div className="space-y-2">
          {files.map(f => (
            <div key={f.id} className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-3">
              <div className="text-sm font-medium">{f.title || f.path || `File #${f.id}`}</div>
              <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                {f.kind && <span>{f.kind}</span>}
                {f.ext && <span className="bg-gray-700 px-1.5 py-0.5 rounded">.{f.ext}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
