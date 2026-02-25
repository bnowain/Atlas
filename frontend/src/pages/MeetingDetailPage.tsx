import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, ExternalLink, Loader2, FileText, Users, Vote, Mic, Video } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import {
  getMeeting, getSegments, getVotes, getMediaFiles, getPeople, mediaStreamUrl,
} from '../api/meetings'
import type { MeetingDetail, TranscriptSegment, VoteRecord, MediaFile, PersonSummary } from '../api/meetings'
import { formatDate } from '../utils/formatters'
import { spokeUrl } from '../utils/spokeUrl'

type Tab = 'summary' | 'speakers' | 'votes' | 'documents'

interface Speaker {
  person_id: string
  name: string
  segment_count: number
  verified_segments: number
}

const MARKDOWN_COMPONENTS = {
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="text-xl font-semibold mt-4 mb-2 text-gray-100">{children}</h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="text-lg font-semibold mt-3 mb-1.5 text-gray-100">{children}</h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="text-base font-semibold mt-2 mb-1 text-gray-200">{children}</h3>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="mb-2 leading-relaxed text-gray-300">{children}</p>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="list-disc list-inside mb-2 space-y-0.5 text-gray-300">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="list-decimal list-inside mb-2 space-y-0.5 text-gray-300">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="ml-2">{children}</li>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold text-gray-200">{children}</strong>
  ),
  em: ({ children }: { children?: React.ReactNode }) => (
    <em className="italic">{children}</em>
  ),
  code: ({ children, className }: { children?: React.ReactNode; className?: string }) => {
    const isBlock = className?.includes('language-')
    if (isBlock) return <code className="font-mono text-sm text-gray-300">{children}</code>
    return <code className="font-mono text-sm bg-gray-700 px-1 py-0.5 rounded text-gray-200">{children}</code>
  },
  pre: ({ children }: { children?: React.ReactNode }) => (
    <pre className="bg-gray-900 rounded-lg p-3 mb-2 overflow-x-auto text-sm">{children}</pre>
  ),
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className="border-l-2 border-gray-600 pl-3 text-gray-400 mb-2">{children}</blockquote>
  ),
  hr: () => <hr className="border-gray-700 my-3" />,
  a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
      {children}
    </a>
  ),
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="overflow-x-auto mb-2">
      <table className="text-sm border-collapse w-full">{children}</table>
    </div>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="border border-gray-700 px-3 py-1.5 text-left text-gray-300 bg-gray-800/50">{children}</th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="border border-gray-700 px-3 py-1.5 text-gray-400">{children}</td>
  ),
}

function voteOutcomeClass(outcome: string | null): string {
  if (!outcome) return 'bg-gray-700 text-gray-400'
  const lower = outcome.toLowerCase()
  if (lower.includes('carried') || lower.includes('pass') || lower.includes('approved') || lower.includes('adopt')) {
    return 'bg-green-500/20 text-green-400'
  }
  if (lower.includes('fail') || lower.includes('denied') || lower.includes('rejected')) {
    return 'bg-red-500/20 text-red-400'
  }
  return 'bg-gray-700 text-gray-400'
}

function voteValueClass(vote: string): string {
  const lower = vote.toLowerCase()
  if (lower === 'aye' || lower === 'yes') return 'text-green-400'
  if (lower === 'no' || lower === 'noe') return 'text-red-400'
  if (lower === 'abstain') return 'text-yellow-400'
  return 'text-gray-500'
}

export default function MeetingDetailPage() {
  const { meetingId } = useParams<{ meetingId: string }>()
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null)
  const [segments, setSegments] = useState<TranscriptSegment[]>([])
  const [votes, setVotes] = useState<VoteRecord[]>([])
  const [mediaFiles, setMediaFiles] = useState<MediaFile[]>([])
  const [speakers, setSpeakers] = useState<Speaker[]>([])
  const [activeTab, setActiveTab] = useState<Tab>('summary')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!meetingId) return
    setLoading(true)

    Promise.all([
      getMeeting(meetingId),
      getSegments(meetingId),
      getVotes(meetingId),
      getMediaFiles(meetingId),
      getPeople(),
    ])
      .then(([mtg, segs, vts, media, people]) => {
        setMeeting(mtg)
        setSegments(segs)
        setVotes(vts)
        setMediaFiles(media)

        // Build name map from people list
        const nameMap: Record<string, string> = {}
        for (const p of people) {
          nameMap[p.person_id] = p.canonical_name
        }

        // Derive speakers from segment assignments
        const countMap: Record<string, number> = {}
        const verifiedMap: Record<string, number> = {}
        for (const seg of segs) {
          const pid = seg.assignment?.predicted_person_id
          if (pid) {
            countMap[pid] = (countMap[pid] || 0) + 1
            if (seg.assignment?.verified) {
              verifiedMap[pid] = (verifiedMap[pid] || 0) + 1
            }
          }
        }

        const spks: Speaker[] = Object.entries(countMap)
          .map(([pid, cnt]) => ({
            person_id: pid,
            name: nameMap[pid] || `Unknown (${pid.slice(0, 8)}...)`,
            segment_count: cnt,
            verified_segments: verifiedMap[pid] || 0,
          }))
          .filter(s => !['ignore', 'unknown', 'unknown speaker'].includes(s.name.toLowerCase()))
          .sort((a, b) => b.segment_count - a.segment_count)
        setSpeakers(spks)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [meetingId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-gray-500" />
      </div>
    )
  }

  if (error || !meeting) {
    return <div className="p-6 text-red-400">{error || 'Meeting not found'}</div>
  }

  // Determine media type
  const primaryMedia = mediaFiles.find(f => f.file_type === 'video' || f.file_type === 'audio')
  const isVideo = primaryMedia?.file_type === 'video'
  const isAudio = primaryMedia?.file_type === 'audio'
  const hasMedia = isVideo || isAudio

  const tabs: [Tab, string, typeof FileText][] = [
    ['summary', 'Summary', FileText],
    ['speakers', speakers.length ? `Speakers (${speakers.length})` : 'Speakers', Users],
    ['votes', votes.length ? `Votes (${votes.length})` : 'Votes', Vote as typeof FileText],
    ['documents', 'Documents', FileText],
  ]

  return (
    <div className="max-w-4xl mx-auto px-3 md:px-6 py-4 md:py-8">
      {/* Header */}
      <div className="flex items-start gap-3 mb-6">
        <Link
          to="/meetings"
          className="p-1.5 mt-0.5 rounded-lg hover:bg-gray-800 transition-colors shrink-0"
          title="Back to meetings"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold leading-tight">
            {meeting.title || `Meeting ${meetingId?.slice(0, 8)}...`}
          </h1>
          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500 mt-1">
            {meeting.meeting_date && <span>{formatDate(meeting.meeting_date)}</span>}
            {meeting.governing_body && (
              <><span>&middot;</span><span>{meeting.governing_body}</span></>
            )}
            {meeting.meeting_type && (
              <><span>&middot;</span><span>{meeting.meeting_type}</span></>
            )}
            {hasMedia && (
              <>
                <span>&middot;</span>
                <span className="flex items-center gap-0.5">
                  {isVideo ? <Video className="w-3 h-3" /> : <Mic className="w-3 h-3" />}
                  {isVideo ? 'Video' : 'Audio'}
                </span>
              </>
            )}
          </div>
        </div>
        <a
          href={spokeUrl(8000, `/review/${meetingId}`)}
          target="_blank"
          rel="noopener noreferrer"
          className="p-1.5 rounded-lg hover:bg-gray-800 transition-colors shrink-0"
          title="Open in Civic Media"
        >
          <ExternalLink className="w-4 h-4 text-gray-500" />
        </a>
      </div>

      {/* Media player */}
      {hasMedia && meetingId && (
        <div className="mb-6 rounded-xl overflow-hidden bg-black border border-gray-800">
          {isVideo ? (
            <video
              controls
              className="w-full max-h-80"
              src={mediaStreamUrl(meetingId)}
            />
          ) : (
            <div className="p-4">
              <audio
                controls
                className="w-full"
                src={mediaStreamUrl(meetingId)}
              />
            </div>
          )}
        </div>
      )}

      {/* Tab bar */}
      <div className="flex border-b border-gray-800 mb-6 overflow-x-auto">
        {tabs.map(([tab, label, Icon]) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 whitespace-nowrap transition-colors ${
              activeTab === tab
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'summary' && (
        <div>
          {meeting.summary_long ? (
            <ReactMarkdown components={MARKDOWN_COMPONENTS as any}>
              {meeting.summary_long}
            </ReactMarkdown>
          ) : meeting.summary_short ? (
            <p className="text-gray-300 leading-relaxed">{meeting.summary_short}</p>
          ) : (
            <p className="text-gray-500 text-sm">No summary available for this meeting.</p>
          )}
        </div>
      )}

      {activeTab === 'speakers' && (
        <div className="space-y-2">
          {speakers.length === 0 ? (
            <p className="text-gray-500 text-sm">
              No identified speakers found in this meeting's transcript.
            </p>
          ) : (
            speakers.map(s => (
              <div
                key={s.person_id}
                className="flex items-center justify-between bg-gray-800 rounded-xl px-4 py-3"
              >
                <div className="font-medium text-sm">{s.name}</div>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span>{s.segment_count} segments</span>
                  {s.verified_segments > 0 && (
                    <span className="text-green-400">{s.verified_segments} verified</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'votes' && (
        <div className="space-y-4">
          {votes.length === 0 ? (
            <p className="text-gray-500 text-sm">No vote records found for this meeting.</p>
          ) : (
            votes.map((v, i) => (
              <div key={v.vote_id || i} className="bg-gray-800 rounded-xl p-4">
                {v.agenda_section && (
                  <div className="text-xs text-gray-500 mb-1">{v.agenda_section}</div>
                )}
                <div className="text-sm font-medium mb-2">
                  {v.item_description || 'Motion'}
                </div>
                <div className="flex flex-wrap items-center gap-3 mb-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${voteOutcomeClass(v.outcome)}`}>
                    {v.outcome || 'Unknown'}
                  </span>
                  {v.vote_tally && (
                    <span className="text-xs text-gray-500">{v.vote_tally}</span>
                  )}
                  {v.mover && (
                    <span className="text-xs text-gray-500">Mover: {v.mover}</span>
                  )}
                  {v.seconder && (
                    <span className="text-xs text-gray-500">Seconder: {v.seconder}</span>
                  )}
                </div>
                {v.members && v.members.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {v.members.map((m, j) => (
                      <div key={j} className="text-xs">
                        <span className="text-gray-300">{m.name}</span>
                        <span className={`ml-1 font-medium ${voteValueClass(m.vote)}`}>
                          {m.vote}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {v.resolution_number && (
                  <div className="text-xs text-gray-600 mt-2">Res. {v.resolution_number}</div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'documents' && (
        <div className="space-y-2">
          {!meeting.agenda_url && !meeting.minutes_url && !meeting.packet_url ? (
            <p className="text-gray-500 text-sm">No document links available for this meeting.</p>
          ) : (
            <>
              {meeting.agenda_url && (
                <a
                  href={meeting.agenda_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 hover:border-blue-500/30 transition-colors"
                >
                  <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                  <span className="text-sm">Agenda</span>
                  <ExternalLink className="w-3 h-3 text-gray-500 ml-auto shrink-0" />
                </a>
              )}
              {meeting.minutes_url && (
                <a
                  href={meeting.minutes_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 hover:border-blue-500/30 transition-colors"
                >
                  <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                  <span className="text-sm">Minutes</span>
                  <ExternalLink className="w-3 h-3 text-gray-500 ml-auto shrink-0" />
                </a>
              )}
              {meeting.packet_url && (
                <a
                  href={meeting.packet_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 hover:border-blue-500/30 transition-colors"
                >
                  <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                  <span className="text-sm">Packet</span>
                  <ExternalLink className="w-3 h-3 text-gray-500 ml-auto shrink-0" />
                </a>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
