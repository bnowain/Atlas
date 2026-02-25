import { useState, useEffect } from 'react'
import { ExternalLink, Loader2 } from 'lucide-react'
import { apiFetch } from '../api/client'
import { formatDate } from '../utils/formatters'
import { spokeUrl } from '../utils/spokeUrl'

interface Article {
  id: number
  title: string
  source: string
  url: string
  published: string | null
  category: string | null
}

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFetch<Article[]>('/spokes/article_tracker/api/articles?limit=50')
      .then(data => setArticles(Array.isArray(data) ? data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-full"><Loader2 className="w-6 h-6 animate-spin text-gray-500" /></div>
  if (error) return <div className="p-6 text-red-400">{error}</div>

  return (
    <div className="max-w-4xl mx-auto px-3 md:px-6 py-4 md:py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Articles</h1>
        <a href={spokeUrl(5000)} target="_blank" rel="noopener noreferrer" className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1">
          Open Article Tracker <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {articles.length === 0 ? (
        <div className="text-gray-500 text-sm">No articles found</div>
      ) : (
        <div className="space-y-2">
          {articles.map(a => (
            <a
              key={a.id}
              href={a.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 hover:border-amber-500/30 transition-colors"
            >
              <div className="text-sm font-medium">{a.title}</div>
              <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                <span>{a.source}</span>
                {a.category && <><span>&middot;</span><span>{a.category}</span></>}
                {a.published && <><span>&middot;</span><span>{formatDate(a.published)}</span></>}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
