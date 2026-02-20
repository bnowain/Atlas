import SpokeCard from './SpokeCard'
import type { SpokeStatus } from '../../api/types'

interface DashboardGridProps {
  spokes: SpokeStatus[]
}

export default function DashboardGrid({ spokes }: DashboardGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {spokes.map(spoke => (
        <SpokeCard key={spoke.key} spoke={spoke} />
      ))}
    </div>
  )
}
