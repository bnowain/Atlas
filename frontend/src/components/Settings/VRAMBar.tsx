import type { GPUInfo } from '../../api/types'

interface VRAMBarProps {
  gpu: GPUInfo
}

export default function VRAMBar({ gpu }: VRAMBarProps) {
  const pct = Math.min((gpu.used_vram_gb / gpu.total_vram_gb) * 100, 100)
  const color =
    pct > 90 ? 'bg-red-500' :
    pct > 70 ? 'bg-yellow-500' :
    'bg-blue-500'

  return (
    <div className="mb-5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-gray-400">{gpu.name}</span>
        <span className="text-xs text-gray-300 font-mono">
          {gpu.used_vram_gb.toFixed(1)} / {gpu.total_vram_gb.toFixed(1)} GB
        </span>
      </div>
      <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center justify-between mt-1">
        <span className="text-xs text-gray-500">
          {gpu.models_loaded} model{gpu.models_loaded !== 1 ? 's' : ''} loaded
          {gpu.estimated_loaded_gb > 0 && ` (~${gpu.estimated_loaded_gb.toFixed(1)} GB estimated)`}
        </span>
        <span className="text-xs text-gray-500">
          {gpu.available_vram_gb.toFixed(1)} GB available
        </span>
      </div>
    </div>
  )
}
