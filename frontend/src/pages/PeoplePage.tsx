import { useState, useEffect } from 'react'
import { Loader2, Users } from 'lucide-react'
import { apiFetch } from '../api/client'
import { spokeLabel, spokeColor } from '../utils/formatters'
import type { UnifiedPerson } from '../api/types'

export default function PeoplePage() {
  const [people, setPeople] = useState<UnifiedPerson[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFetch<UnifiedPerson[]>('/people')
      .then(setPeople)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-full"><Loader2 className="w-6 h-6 animate-spin text-gray-500" /></div>

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-center gap-2 mb-6">
        <Users className="w-5 h-5 text-gray-400" />
        <h1 className="text-xl font-semibold">People</h1>
      </div>

      {error && <div className="text-red-400 mb-4">{error}</div>}

      {people.length === 0 ? (
        <div className="text-gray-500 text-sm">
          No unified people records yet. People will appear here as you link identities across apps.
        </div>
      ) : (
        <div className="space-y-3">
          {people.map(p => (
            <div key={p.id} className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-3">
              <div className="text-sm font-medium">{p.display_name}</div>
              {p.notes && <div className="text-xs text-gray-500 mt-0.5">{p.notes}</div>}
              <div className="flex items-center gap-2 mt-2">
                {p.mappings.map(m => (
                  <span key={m.id} className={`text-xs px-2 py-0.5 rounded-full bg-gray-700 ${spokeColor(m.spoke_key)}`}>
                    {spokeLabel(m.spoke_key)}: {m.spoke_person_name || m.spoke_person_id}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
