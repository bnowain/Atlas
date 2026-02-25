import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, MessageSquare, X } from 'lucide-react'
import { useResults } from '../stores/resultsStore'
import FilterSidebar from '../components/Results/FilterSidebar'
import ResultCard from '../components/Results/ResultCard'
import ResultsChat from '../components/Results/ResultsChat'
import type { ResultItem } from '../stores/resultsStore'

interface FilterState {
  sources: Set<string>
  types: Set<string>
  minRelevance: number
}

function makeDefaultFilters(items: ResultItem[]): FilterState {
  return {
    sources: new Set(items.map(i => i.source)),
    types: new Set(items.map(i => i.type)),
    minRelevance: 0,
  }
}

function applyFilters(items: ResultItem[], filters: FilterState): ResultItem[] {
  return items.filter(item => {
    if (!filters.sources.has(item.source)) return false
    if (!filters.types.has(item.type)) return false
    if (item.relevanceScore !== null && item.relevanceScore < filters.minRelevance) return false
    return true
  })
}

export default function ResultsPage() {
  const { items, query } = useResults()
  const [filters, setFilters] = useState<FilterState>(() => makeDefaultFilters(items))
  const [showChat, setShowChat] = useState(false)

  // Reset filters whenever a new batch of results arrives
  useEffect(() => {
    setFilters(makeDefaultFilters(items))
  }, [items])

  const filtered = applyFilters(items, filters)
  const uniqueSpokes = [...new Set(items.map(i => i.source))]

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-gray-500">
        <p className="text-sm">No results to display.</p>
        <Link to="/chat" className="text-blue-400 hover:underline text-sm flex items-center gap-1">
          <ArrowLeft className="w-3 h-3" />
          Back to chat
        </Link>
      </div>
    )
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: filters */}
      <div className="hidden md:block w-56 shrink-0 border-r border-gray-800 overflow-y-auto p-4">
        <FilterSidebar items={items} filters={filters} onChange={setFilters} />
      </div>

      {/* Center: results grid */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 shrink-0">
          <Link to="/chat" className="p-1 rounded hover:bg-gray-800 transition-colors">
            <ArrowLeft className="w-4 h-4 text-gray-500" />
          </Link>
          <div className="flex-1 min-w-0">
            {query && (
              <span className="text-sm text-gray-400 truncate">
                Results for: <span className="text-gray-200">"{query}"</span>
              </span>
            )}
          </div>
          <span className="text-xs text-gray-500 shrink-0">
            {filtered.length} of {items.length} results
          </span>
          <button
            onClick={() => setShowChat(!showChat)}
            className={`p-1.5 rounded-lg transition-colors shrink-0 ${
              showChat ? 'bg-gray-700 text-blue-400' : 'hover:bg-gray-800 text-gray-500'
            }`}
            title="Toggle chat"
          >
            <MessageSquare className="w-4 h-4" />
          </button>
        </div>

        {/* Mobile filter bar */}
        <div className="md:hidden px-4 py-2 border-b border-gray-800 flex items-center gap-2 overflow-x-auto">
          <span className="text-xs text-gray-500 shrink-0">Filter:</span>
          {[...new Set(items.map(i => i.source))].map(source => (
            <button
              key={source}
              onClick={() => {
                const next = new Set(filters.sources)
                if (next.has(source)) next.delete(source)
                else next.add(source)
                setFilters({ ...filters, sources: next })
              }}
              className={`px-2 py-0.5 rounded-full text-xs border transition-colors shrink-0 ${
                filters.sources.has(source)
                  ? 'bg-blue-500/20 border-blue-500/40 text-blue-400'
                  : 'border-gray-700 text-gray-600'
              }`}
            >
              {source}
            </button>
          ))}
        </div>

        {/* Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {filtered.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
              No results match the current filters.
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {filtered.map(item => (
                <ResultCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right: chat panel */}
      {showChat && (
        <div className="w-80 shrink-0 flex flex-col h-full">
          <ResultsChat query={query} spokes={uniqueSpokes} />
        </div>
      )}
    </div>
  )
}
