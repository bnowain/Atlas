import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronDown, ChevronRight, Check, X, Loader2, ArrowRight } from 'lucide-react'
import { spokeLabel, spokeColor, formatDate } from '../../utils/formatters'
import { setResults } from '../../stores/resultsStore'
import type { ResultItem } from '../../stores/resultsStore'
import type { ToolCallRecord } from '../../api/types'

function toolLabel(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function toolSpoke(name: string): string {
  const map: Record<string, string> = {
    search_meetings: 'civic_media', get_transcript: 'civic_media',
    search_speakers: 'civic_media', get_speaker_appearances: 'civic_media',
    get_meeting_speakers: 'civic_media', export_transcript: 'civic_media',
    get_meeting_votes: 'civic_media', search_votes: 'civic_media',
    search_brown_act: 'civic_media',
    search_articles: 'article_tracker', get_article_stats: 'article_tracker',
    get_recent_articles: 'article_tracker',
    search_files: 'shasta_db', list_archive_people: 'shasta_db', get_file_info: 'shasta_db',
    search_messages: 'facebook_offline', search_posts: 'facebook_offline',
    list_threads: 'facebook_offline', get_thread_messages: 'facebook_offline',
    search_people_fb: 'facebook_offline',
    search_pra_requests: 'shasta_pra', get_pra_request: 'shasta_pra',
    list_pra_departments: 'shasta_pra', get_pra_stats: 'shasta_pra', search_pra_all: 'shasta_pra',
    search_campaign_filers: 'campaign_finance', get_campaign_filer: 'campaign_finance',
    search_campaign_transactions: 'campaign_finance', search_campaign_filings: 'campaign_finance',
    get_campaign_stats: 'campaign_finance', search_campaign_people: 'campaign_finance',
    search_monitored_posts: 'facebook_monitor', get_monitored_post: 'facebook_monitor',
    search_monitored_people: 'facebook_monitor', list_monitored_pages: 'facebook_monitor',
    get_fb_monitor_entities: 'facebook_monitor',
    search_atlas_people: 'atlas', semantic_search: 'atlas',
  }
  return map[name] || 'unknown'
}

const MEETING_TOOLS = new Set(['search_meetings'])
const VOTE_TOOLS = new Set(['search_votes', 'get_meeting_votes'])

function isMeetingRecord(item: unknown): item is { meeting_id: string; title?: string; meeting_date?: string; governing_body?: string } {
  return typeof item === 'object' && item !== null && 'meeting_id' in item
}

function isVoteRecord(item: unknown): item is { meeting_id: string; vote_id: string; outcome?: string; item_description?: string; meeting_date?: string } {
  return typeof item === 'object' && item !== null && 'vote_id' in item
}

/** Extract a human-readable title from any result object. */
function itemTitle(item: unknown): string {
  if (typeof item !== 'object' || !item) return String(item)
  const o = item as Record<string, unknown>
  const val = o.title ?? o.subject ?? o.name ?? o.canonical_name ??
    o.item_description ?? o.display_name ?? o.pretty_id ?? o.question ?? o.text
  if (!val) return 'Result'
  return String(val).slice(0, 120)
}

/** Extract a secondary line (date + category/status). */
function itemMeta(item: unknown): string | null {
  if (typeof item !== 'object' || !item) return null
  const o = item as Record<string, unknown>
  const parts: string[] = []
  const dateStr = String(o.meeting_date ?? o.date ?? o.published_at ?? o.submitted_on ?? o.air_date ?? '')
  if (dateStr) {
    try { parts.push(formatDate(dateStr)) } catch { parts.push(dateStr) }
  }
  const label = o.governing_body ?? o.status ?? o.source ?? o.station ?? o.spoke_key ?? o.schedule
  if (label) parts.push(String(label))
  return parts.length ? parts.join(' · ') : null
}

function mapToResultItems(toolName: string, data: unknown[]): ResultItem[] {
  if (MEETING_TOOLS.has(toolName)) {
    return data.filter(isMeetingRecord).map(m => ({
      id: m.meeting_id, source: 'civic_media', type: 'video',
      title: m.title || `Meeting ${m.meeting_id.slice(0, 8)}`,
      snippet: null, date: m.meeting_date || null, thumbnailUrl: null,
      url: `/meetings/${m.meeting_id}`, relevanceScore: null,
      metadata: { governing_body: m.governing_body },
    }))
  }
  if (VOTE_TOOLS.has(toolName)) {
    return data.filter(isVoteRecord).map((v, i) => ({
      id: `${v.meeting_id}_${i}`, source: 'civic_media', type: 'vote',
      title: v.item_description || 'Vote', snippet: v.outcome || null,
      date: v.meeting_date || null, thumbnailUrl: null,
      url: `/meetings/${v.meeting_id}`, relevanceScore: null, metadata: {},
    }))
  }
  return data.map((item, i) => ({
    id: String(i), source: toolSpoke(toolName), type: 'text',
    title: itemTitle(item), snippet: null, date: null, thumbnailUrl: null,
    url: '/', relevanceScore: null, metadata: {},
  }))
}

// ── Card components ──────────────────────────────────────────────────────────

function MeetingCard({ item }: { item: { meeting_id: string; title?: string; meeting_date?: string; governing_body?: string } }) {
  return (
    <Link
      to={`/meetings/${item.meeting_id}`}
      className="block bg-gray-800/80 border border-gray-700 rounded-lg px-3 py-2 hover:border-blue-500/30 transition-colors"
    >
      <div className="text-xs font-medium text-gray-200 truncate">
        {item.title || `Meeting ${item.meeting_id.slice(0, 8)}…`}
      </div>
      <div className="flex items-center gap-1.5 text-[10px] text-gray-500 mt-0.5">
        {item.meeting_date && <span>{formatDate(item.meeting_date)}</span>}
        {item.governing_body && <><span>&middot;</span><span className="truncate">{item.governing_body}</span></>}
      </div>
    </Link>
  )
}

function VoteCard({ item }: { item: { meeting_id: string; outcome?: string; item_description?: string; meeting_date?: string } }) {
  const isPositive = !!item.outcome?.toLowerCase().match(/carried|passed|approved|adopted/)
  return (
    <Link
      to={`/meetings/${item.meeting_id}`}
      className="block bg-gray-800/80 border border-gray-700 rounded-lg px-3 py-2 hover:border-blue-500/30 transition-colors"
    >
      <div className="text-xs font-medium text-gray-200 truncate">{item.item_description || 'Vote'}</div>
      <div className="flex items-center gap-1.5 text-[10px] mt-0.5">
        {item.outcome && (
          <span className={isPositive ? 'text-green-400' : 'text-red-400'}>{item.outcome}</span>
        )}
        {item.meeting_date && (
          <><span className="text-gray-500">&middot;</span><span className="text-gray-500">{formatDate(item.meeting_date)}</span></>
        )}
      </div>
    </Link>
  )
}

/** Generic readable list for non-meeting tools (no raw JSON). */
function SmartList({ data }: { data: unknown[] }) {
  return (
    <div className="space-y-1 max-h-52 overflow-y-auto">
      {data.map((item, i) => {
        const meta = itemMeta(item)
        return (
          <div key={i} className="bg-gray-800/60 rounded px-2 py-1.5">
            <div className="text-[11px] text-gray-200 truncate">{itemTitle(item)}</div>
            {meta && <div className="text-[10px] text-gray-500 truncate">{meta}</div>}
          </div>
        )
      })}
    </div>
  )
}

// ── Main component ───────────────────────────────────────────────────────────

export default function ToolCallIndicator({ toolCall }: { toolCall: ToolCallRecord }) {
  const [expanded, setExpanded] = useState(false)
  const navigate = useNavigate()
  const spoke = toolSpoke(toolCall.name)
  const hasResult = toolCall.result?.success !== undefined
  const success = toolCall.result?.success
  const resultData = toolCall.result?.data

  const resultArray = Array.isArray(resultData) ? resultData : null
  const resultCount = resultArray?.length ?? null

  const isMeetingTool = MEETING_TOOLS.has(toolCall.name)
  const isVoteTool = VOTE_TOOLS.has(toolCall.name)
  const hasRichCards = (isMeetingTool || isVoteTool) && !!resultArray?.length && success

  function handleViewAll() {
    if (!resultArray) return
    const query = String(toolCall.arguments?.query ?? toolCall.arguments?.q ?? '')
    setResults(mapToResultItems(toolCall.name, resultArray), query)
    navigate('/results')
  }

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden text-xs">
      {/* Header row — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-800/50 transition-colors"
      >
        {!hasResult ? (
          <Loader2 className="w-3 h-3 animate-spin text-gray-400 shrink-0" />
        ) : success ? (
          <Check className="w-3 h-3 text-green-400 shrink-0" />
        ) : (
          <X className="w-3 h-3 text-red-400 shrink-0" />
        )}
        <span className={spoke === 'atlas' ? 'text-gray-300' : spokeColor(spoke)}>
          {spoke === 'atlas' ? 'Atlas' : spokeLabel(spoke)}
        </span>
        <span className="text-gray-400">&middot;</span>
        <span className="text-gray-300">{toolLabel(toolCall.name)}</span>
        {resultCount !== null && (
          <span className="text-gray-500">({resultCount})</span>
        )}
        {/* "View all" inline in header for 3+ results — no need to expand first */}
        {success && resultCount !== null && resultCount >= 3 && (
          <button
            onClick={e => { e.stopPropagation(); handleViewAll() }}
            className="ml-auto flex items-center gap-0.5 text-blue-400 hover:text-blue-300 transition-colors mr-1"
          >
            View all <ArrowRight className="w-3 h-3" />
          </button>
        )}
        <span className={success && resultCount !== null && resultCount >= 3 ? '' : 'ml-auto'}>
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </span>
      </button>

      {/* Expanded panel */}
      {expanded && hasResult && (
        <div className="border-t border-gray-700 px-3 py-2 bg-gray-900/50">
          {success ? (
            <>
              {/* Meeting cards */}
              {hasRichCards && (
                <div className="space-y-1.5 max-h-52 overflow-y-auto">
                  {isMeetingTool && resultArray!.filter(isMeetingRecord).map((item, i) => (
                    <MeetingCard key={i} item={item} />
                  ))}
                  {isVoteTool && resultArray!.filter(isVoteRecord).map((item, i) => (
                    <VoteCard key={i} item={item} />
                  ))}
                </div>
              )}

              {/* Smart list for non-rich tools */}
              {!hasRichCards && resultArray && resultArray.length > 0 && (
                <SmartList data={resultArray} />
              )}

              {/* Non-array result (single object / stats) */}
              {!resultArray && resultData !== undefined && (
                <div className="text-[11px] text-gray-400">
                  {typeof resultData === 'object'
                    ? Object.entries(resultData as Record<string, unknown>)
                        .slice(0, 8)
                        .map(([k, v]) => (
                          <div key={k}>
                            <span className="text-gray-500">{k}:</span>{' '}
                            <span className="text-gray-300">{String(v)}</span>
                          </div>
                        ))
                    : String(resultData)
                  }
                </div>
              )}

              {resultCount === 0 && (
                <div className="text-gray-500 text-[11px]">No results returned.</div>
              )}
            </>
          ) : (
            <div className="text-red-400 text-[11px]">{toolCall.result?.error || 'Tool failed'}</div>
          )}
        </div>
      )}
    </div>
  )
}
