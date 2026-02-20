import { ExternalLink } from 'lucide-react'
import type { SpokeStatus } from '../../api/types'
import { spokeLabel, spokeBg } from '../../utils/formatters'

interface SpokeCardProps {
  spoke: SpokeStatus
}

const spokeDescriptions: Record<string, string> = {
  civic_media: 'Meeting transcripts & speaker identification',
  article_tracker: 'Local news aggregation & monitoring',
  shasta_db: 'Civic media archive browser',
  facebook_offline: 'Personal Facebook archive (private)',
}

const spokeIcons: Record<string, string> = {
  civic_media: 'V',  // Video
  article_tracker: 'N',  // News
  shasta_db: 'A',  // Archive
  facebook_offline: 'M',  // Messages
}

export default function SpokeCard({ spoke }: SpokeCardProps) {
  return (
    <div className={`rounded-xl border p-4 ${spokeBg(spoke.key)}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-medium text-sm">{spokeLabel(spoke.key)}</h3>
          <p className="text-xs text-gray-500 mt-0.5">{spokeDescriptions[spoke.key]}</p>
        </div>
        <span
          className={`flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full ${
            spoke.online
              ? 'bg-green-500/10 text-green-400'
              : 'bg-red-500/10 text-red-400'
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${spoke.online ? 'bg-green-400' : 'bg-red-400'}`} />
          {spoke.online ? 'Online' : 'Offline'}
        </span>
      </div>

      {spoke.online && spoke.latency_ms != null && (
        <div className="text-xs text-gray-500">
          Latency: {spoke.latency_ms}ms
        </div>
      )}
      {!spoke.online && spoke.error && (
        <div className="text-xs text-red-400/70 truncate">
          {spoke.error}
        </div>
      )}

      <div className="mt-3 flex items-center gap-2">
        <a
          href={spoke.base_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1 transition-colors"
        >
          {spoke.base_url} <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  )
}
