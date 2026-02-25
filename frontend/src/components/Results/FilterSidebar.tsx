import { spokeLabel, spokeColor } from '../../utils/formatters'
import type { ResultItem } from '../../stores/resultsStore'

interface FilterState {
  sources: Set<string>
  types: Set<string>
  minRelevance: number
}

interface FilterSidebarProps {
  items: ResultItem[]
  filters: FilterState
  onChange: (filters: FilterState) => void
}

const ALL_TYPES = [
  { key: 'video', label: 'Video' },
  { key: 'audio', label: 'Audio' },
  { key: 'vote', label: 'Vote' },
  { key: 'document', label: 'Document' },
  { key: 'article', label: 'Article' },
  { key: 'text', label: 'Text' },
  { key: 'message', label: 'Message' },
]

export default function FilterSidebar({ items, filters, onChange }: FilterSidebarProps) {
  // Derive unique sources from items
  const availableSources = [...new Set(items.map(i => i.source))].sort()
  const availableTypes = ALL_TYPES.filter(t => items.some(i => i.type === t.key))
  const hasRelevance = items.some(i => i.relevanceScore !== null)

  function toggleSource(source: string) {
    const next = new Set(filters.sources)
    if (next.has(source)) next.delete(source)
    else next.add(source)
    onChange({ ...filters, sources: next })
  }

  function toggleType(type: string) {
    const next = new Set(filters.types)
    if (next.has(type)) next.delete(type)
    else next.add(type)
    onChange({ ...filters, types: next })
  }

  function selectAll() {
    onChange({
      sources: new Set(availableSources),
      types: new Set(availableTypes.map(t => t.key)),
      minRelevance: 0,
    })
  }

  return (
    <div className="w-52 shrink-0 space-y-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Filters</span>
        <button
          onClick={selectAll}
          className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors"
        >
          Clear all
        </button>
      </div>

      {/* Source filter */}
      {availableSources.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 mb-2">Source</div>
          <div className="space-y-1.5">
            {availableSources.map(source => (
              <label key={source} className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={filters.sources.has(source)}
                  onChange={() => toggleSource(source)}
                  className="w-3.5 h-3.5 rounded border-gray-600 bg-gray-800 accent-blue-500"
                />
                <span className={`text-xs ${spokeColor(source)} group-hover:brightness-125 transition-all`}>
                  {spokeLabel(source)}
                </span>
                <span className="text-[10px] text-gray-600 ml-auto">
                  {items.filter(i => i.source === source).length}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Type filter */}
      {availableTypes.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 mb-2">Type</div>
          <div className="space-y-1.5">
            {availableTypes.map(({ key, label }) => (
              <label key={key} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.types.has(key)}
                  onChange={() => toggleType(key)}
                  className="w-3.5 h-3.5 rounded border-gray-600 bg-gray-800 accent-blue-500"
                />
                <span className="text-xs text-gray-300">{label}</span>
                <span className="text-[10px] text-gray-600 ml-auto">
                  {items.filter(i => i.type === key).length}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Relevance slider */}
      {hasRelevance && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500">Min Relevance</span>
            <span className="text-xs text-gray-400">{Math.round(filters.minRelevance * 100)}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={filters.minRelevance}
            onChange={e => onChange({ ...filters, minRelevance: parseFloat(e.target.value) })}
            className="w-full accent-blue-500"
          />
        </div>
      )}
    </div>
  )
}
