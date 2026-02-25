import { Link } from 'react-router-dom'
import { Video, Mic, FileText, MessageSquare, Vote, Newspaper, ExternalLink } from 'lucide-react'
import { spokeLabel, spokeColor, spokeBg, formatDate } from '../../utils/formatters'
import type { ResultItem } from '../../stores/resultsStore'

function TypeIcon({ type }: { type: string }) {
  const cls = 'w-8 h-8 text-gray-600'
  switch (type) {
    case 'video': return <Video className={cls} />
    case 'audio': return <Mic className={cls} />
    case 'vote': return <Vote className={cls} />
    case 'article': return <Newspaper className={cls} />
    case 'message': return <MessageSquare className={cls} />
    default: return <FileText className={cls} />
  }
}

interface ResultCardProps {
  item: ResultItem
}

function isExternal(url: string) {
  return url.startsWith('http://') || url.startsWith('https://')
}

export default function ResultCard({ item }: ResultCardProps) {
  const external = isExternal(item.url)

  const inner = (
    <div className={`h-full bg-gray-800 border border-gray-700 rounded-xl overflow-hidden hover:border-blue-500/30 transition-colors flex flex-col`}>
      {/* Thumbnail or placeholder */}
      <div className="h-28 bg-gray-900 flex items-center justify-center shrink-0">
        {item.thumbnailUrl ? (
          <img
            src={item.thumbnailUrl}
            alt={item.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <TypeIcon type={item.type} />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 p-3 flex flex-col gap-1 min-w-0">
        {/* Source + type badges */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${spokeBg(item.source)} ${spokeColor(item.source)}`}>
            {spokeLabel(item.source)}
          </span>
          <span className="text-[10px] text-gray-500 capitalize">{item.type}</span>
          {item.relevanceScore !== null && (
            <span className="text-[10px] text-gray-600 ml-auto">
              {Math.round(item.relevanceScore * 100)}%
            </span>
          )}
        </div>

        {/* Title */}
        <div className="text-xs font-medium text-gray-200 line-clamp-2 leading-snug">
          {item.title}
        </div>

        {/* Snippet */}
        {item.snippet && (
          <div className="text-[11px] text-gray-500 line-clamp-2 leading-snug">
            {item.snippet}
          </div>
        )}

        {/* Date + external indicator */}
        <div className="flex items-center gap-1 mt-auto pt-1">
          {item.date && (
            <span className="text-[10px] text-gray-600">{formatDate(item.date)}</span>
          )}
          {external && (
            <ExternalLink className="w-2.5 h-2.5 text-gray-600 ml-auto" />
          )}
        </div>
      </div>
    </div>
  )

  if (external) {
    return (
      <a href={item.url} target="_blank" rel="noopener noreferrer" className="block h-full">
        {inner}
      </a>
    )
  }

  return (
    <Link to={item.url} className="block h-full">
      {inner}
    </Link>
  )
}
