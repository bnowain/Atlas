import { useState } from 'react'
import { ChevronDown, ChevronRight, Check, X, Loader2 } from 'lucide-react'
import { spokeLabel, spokeColor } from '../../utils/formatters'
import type { ToolCallRecord } from '../../api/types'

// Map tool name to a readable label
function toolLabel(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// Map tool name to its spoke
function toolSpoke(name: string): string {
  const map: Record<string, string> = {
    search_meetings: 'civic_media', get_transcript: 'civic_media',
    search_speakers: 'civic_media', get_speaker_appearances: 'civic_media',
    export_transcript: 'civic_media',
    search_articles: 'article_tracker', get_article_stats: 'article_tracker',
    get_recent_articles: 'article_tracker',
    search_files: 'shasta_db', list_archive_people: 'shasta_db',
    get_file_info: 'shasta_db',
    search_messages: 'facebook_offline', search_posts: 'facebook_offline',
    list_threads: 'facebook_offline', get_thread_messages: 'facebook_offline',
    search_people_fb: 'facebook_offline',
  }
  return map[name] || 'unknown'
}

export default function ToolCallIndicator({ toolCall }: { toolCall: ToolCallRecord }) {
  const [expanded, setExpanded] = useState(false)
  const spoke = toolSpoke(toolCall.name)
  const hasResult = toolCall.result?.success !== undefined
  const success = toolCall.result?.success
  const resultData = toolCall.result?.data

  // Count results if array
  let resultCount: number | null = null
  if (Array.isArray(resultData)) {
    resultCount = resultData.length
  }

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden text-xs">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-800/50 transition-colors"
      >
        {!hasResult ? (
          <Loader2 className="w-3 h-3 animate-spin text-gray-400" />
        ) : success ? (
          <Check className="w-3 h-3 text-green-400" />
        ) : (
          <X className="w-3 h-3 text-red-400" />
        )}
        <span className={`${spokeColor(spoke)}`}>{spokeLabel(spoke)}</span>
        <span className="text-gray-400">&middot;</span>
        <span className="text-gray-300">{toolLabel(toolCall.name)}</span>
        {resultCount !== null && (
          <span className="text-gray-500">({resultCount} results)</span>
        )}
        <span className="ml-auto">
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </span>
      </button>
      {expanded && (
        <div className="border-t border-gray-700 px-3 py-2 bg-gray-900/50 max-h-60 overflow-y-auto">
          <div className="text-gray-400 mb-1">Arguments:</div>
          <pre className="text-gray-300 text-[11px] whitespace-pre-wrap">
            {JSON.stringify(toolCall.arguments, null, 2)}
          </pre>
          {hasResult && (
            <>
              <div className="text-gray-400 mt-2 mb-1">Result:</div>
              <pre className="text-gray-300 text-[11px] whitespace-pre-wrap">
                {JSON.stringify(toolCall.result, null, 2).slice(0, 2000)}
              </pre>
            </>
          )}
        </div>
      )}
    </div>
  )
}
