import { useCallback } from 'react'

const SPOKE_DEFS = [
  { key: 'civic_media', label: 'Civic Media' },
  { key: 'article_tracker', label: 'Articles' },
  { key: 'shasta_db', label: 'Shasta-DB' },
  { key: 'facebook_offline', label: 'Facebook' },
] as const

export const ALL_SPOKE_KEYS = SPOKE_DEFS.map(s => s.key)

interface SpokeFilterProps {
  activeSpokes: string[]
  onChange: (spokes: string[]) => void
}

export default function SpokeFilter({ activeSpokes, onChange }: SpokeFilterProps) {
  const isChatOnly = activeSpokes.length === 0

  const toggleChatOnly = useCallback(() => {
    onChange(isChatOnly ? [...ALL_SPOKE_KEYS] : [])
  }, [isChatOnly, onChange])

  const toggleSpoke = useCallback((key: string) => {
    if (activeSpokes.includes(key)) {
      onChange(activeSpokes.filter(k => k !== key))
    } else {
      onChange([...activeSpokes, key])
    }
  }, [activeSpokes, onChange])

  const pillBase = 'px-2.5 py-1 text-xs rounded-full border cursor-pointer select-none transition-colors'
  const active = 'bg-blue-600/20 text-blue-400 border-blue-500/30'
  const inactive = 'bg-gray-800 text-gray-500 border-gray-700 hover:border-gray-600'

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <button
        onClick={toggleChatOnly}
        className={`${pillBase} ${isChatOnly ? active : inactive}`}
      >
        Chat only
      </button>
      {SPOKE_DEFS.map(spoke => (
        <button
          key={spoke.key}
          onClick={() => toggleSpoke(spoke.key)}
          className={`${pillBase} ${activeSpokes.includes(spoke.key) ? active : inactive}`}
        >
          {spoke.label}
        </button>
      ))}
    </div>
  )
}
