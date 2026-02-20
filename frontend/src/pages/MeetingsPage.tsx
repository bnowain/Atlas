import { useState, useEffect } from 'react'
import { ExternalLink, Loader2 } from 'lucide-react'
import { apiFetch } from '../api/client'
import { formatDate } from '../utils/formatters'

interface Meeting {
  meeting_id: string
  title: string | null
  meeting_date: string | null
  governing_body: string | null
  meeting_type: string | null
  created_at: string
}

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFetch<Meeting[]>('/spokes/civic_media/api/meetings')
      .then(setMeetings)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-full"><Loader2 className="w-6 h-6 animate-spin text-gray-500" /></div>
  if (error) return <div className="p-6 text-red-400">{error}</div>

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Meetings</h1>
        <a href="http://localhost:8000" target="_blank" rel="noopener noreferrer" className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1">
          Open Civic Media <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {meetings.length === 0 ? (
        <div className="text-gray-500 text-sm">No meetings found</div>
      ) : (
        <div className="space-y-2">
          {meetings.map(m => (
            <a
              key={m.meeting_id}
              href={`http://localhost:8000/review/${m.meeting_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 hover:border-blue-500/30 transition-colors"
            >
              <div className="text-sm font-medium">{m.title || `Meeting ${m.meeting_id}`}</div>
              <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                {m.meeting_date && <span>{formatDate(m.meeting_date)}</span>}
                {m.governing_body && <><span>&middot;</span><span>{m.governing_body}</span></>}
                {m.meeting_type && <><span>&middot;</span><span>{m.meeting_type}</span></>}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
