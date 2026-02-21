import { useState } from 'react'
import { Loader2, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'
import type { LocalModel } from '../../api/types'
import { getModelLogs } from '../../api/models'

interface ModelCardProps {
  model: LocalModel
  onStart: (key: string) => void
  onStop: (key: string) => void
  canLoad: boolean
}

const stateStyles: Record<string, { dot: string; border: string; label: string }> = {
  running:  { dot: 'bg-green-400', border: 'border-gray-700', label: 'Running' },
  starting: { dot: 'bg-blue-400 animate-pulse', border: 'border-blue-500/40', label: 'Starting...' },
  stopping: { dot: 'bg-yellow-400 animate-pulse', border: 'border-yellow-500/40', label: 'Stopping...' },
  stopped:  { dot: 'bg-gray-600', border: 'border-gray-700', label: 'Stopped' },
  error:    { dot: 'bg-red-500', border: 'border-red-500/40', label: 'Error' },
}

export default function ModelCard({ model, onStart, onStop, canLoad }: ModelCardProps) {
  const [showLogs, setShowLogs] = useState(false)
  const [logs, setLogs] = useState<string | null>(null)
  const [actionPending, setActionPending] = useState(false)

  const style = stateStyles[model.state] || stateStyles.stopped
  const isTransitioning = model.state === 'starting' || model.state === 'stopping'
  const isOn = model.state === 'running' || model.state === 'starting'

  const handleToggle = async () => {
    if (isTransitioning || actionPending) return
    setActionPending(true)
    try {
      if (isOn) {
        await onStop(model.key)
      } else {
        await onStart(model.key)
      }
    } finally {
      setActionPending(false)
    }
  }

  const handleShowLogs = async () => {
    if (!showLogs) {
      try {
        const data = await getModelLogs(model.key)
        setLogs(data.logs)
      } catch {
        setLogs('Failed to load logs')
      }
    }
    setShowLogs(!showLogs)
  }

  const uptime = model.started_at
    ? formatUptime(Date.now() / 1000 - model.started_at)
    : null

  return (
    <div className={`bg-gray-800 border ${style.border} rounded-xl px-4 py-3 transition-colors`}>
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {isTransitioning ? (
            <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin flex-shrink-0" />
          ) : model.state === 'error' ? (
            <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
          ) : (
            <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${style.dot}`} />
          )}
          <span className="text-sm font-medium">{model.name}</span>
          {model.default_on && (
            <span className="text-[10px] text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">default</span>
          )}
        </div>

        {/* Toggle switch */}
        <button
          onClick={handleToggle}
          disabled={isTransitioning || actionPending || (!isOn && !canLoad)}
          title={
            !canLoad && !isOn ? 'Not enough VRAM' :
            isTransitioning ? 'Please wait...' :
            isOn ? 'Stop model' : 'Start model'
          }
          className={`
            relative w-10 h-5 rounded-full transition-colors duration-200 flex-shrink-0
            ${isOn ? 'bg-green-600' : 'bg-gray-600'}
            ${(isTransitioning || actionPending || (!isOn && !canLoad)) ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer hover:brightness-110'}
          `}
        >
          <span className={`
            absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200
            ${isOn ? 'translate-x-5' : 'translate-x-0.5'}
          `} />
        </button>
      </div>

      {/* Model info */}
      <div className="mt-1.5 ml-5">
        <div className="text-xs text-gray-400">{model.model_id}</div>
        <div className="text-xs text-gray-500 mt-0.5">{model.description}</div>

        {/* Stats row */}
        <div className="flex items-center gap-3 mt-2 text-[11px] text-gray-500">
          <span>~{model.vram_gb} GB VRAM</span>
          <span className="text-gray-700">|</span>
          <span>ctx {model.context_length.toLocaleString()}</span>
        </div>

        {/* Status line */}
        <div className="flex items-center gap-2 mt-1.5">
          <span className={`text-xs ${
            model.state === 'running' ? 'text-green-400' :
            model.state === 'error' ? 'text-red-400' :
            model.state === 'starting' ? 'text-blue-400' :
            'text-gray-500'
          }`}>
            {style.label}
          </span>
          {uptime && <span className="text-[11px] text-gray-600">uptime {uptime}</span>}
          {model.state === 'starting' && (
            <span className="text-[11px] text-gray-600">this may take a few minutes</span>
          )}
        </div>

        {/* Error message */}
        {model.state === 'error' && model.error && (
          <div className="mt-2 text-xs text-red-400/80 bg-red-500/5 rounded-lg px-3 py-2 font-mono whitespace-pre-wrap max-h-32 overflow-y-auto">
            {model.error}
          </div>
        )}

        {/* Logs toggle */}
        <button
          onClick={handleShowLogs}
          className="flex items-center gap-1 mt-2 text-[11px] text-gray-500 hover:text-gray-300 transition-colors"
        >
          {showLogs ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {showLogs ? 'Hide info' : 'Show info'}
        </button>
        {showLogs && logs !== null && (
          <pre className="mt-1 text-[10px] text-gray-500 bg-gray-900 rounded-lg px-3 py-2 max-h-48 overflow-y-auto whitespace-pre-wrap">
            {logs}
          </pre>
        )}
      </div>
    </div>
  )
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}
