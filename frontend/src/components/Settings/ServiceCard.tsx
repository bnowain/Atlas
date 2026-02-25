import { useState } from 'react'
import { Loader2, AlertCircle, ChevronDown, ChevronUp, RotateCw } from 'lucide-react'
import type { ServiceStatus } from '../../api/types'
import { getServiceLogs } from '../../api/services'

interface ServiceCardProps {
  service: ServiceStatus
  onStart: (key: string) => void
  onStop: (key: string) => void
  onRestart: (key: string) => void
  onAutoStartToggle: (key: string, enabled: boolean) => void
  depsRunning: boolean
}

const stateStyles: Record<string, { dot: string; border: string; label: string }> = {
  running:  { dot: 'bg-green-400', border: 'border-gray-700', label: 'Running' },
  starting: { dot: 'bg-blue-400 animate-pulse', border: 'border-blue-500/40', label: 'Starting...' },
  stopping: { dot: 'bg-yellow-400 animate-pulse', border: 'border-yellow-500/40', label: 'Stopping...' },
  stopped:  { dot: 'bg-gray-600', border: 'border-gray-700', label: 'Stopped' },
  error:    { dot: 'bg-red-500', border: 'border-red-500/40', label: 'Error' },
}

export default function ServiceCard({ service, onStart, onStop, onRestart, onAutoStartToggle, depsRunning }: ServiceCardProps) {
  const [showLogs, setShowLogs] = useState(false)
  const [logs, setLogs] = useState<string | null>(null)
  const [actionPending, setActionPending] = useState(false)

  const style = stateStyles[service.state] || stateStyles.stopped
  const isTransitioning = service.state === 'starting' || service.state === 'stopping'
  const isOn = service.state === 'running' || service.state === 'starting'

  const handleToggle = async () => {
    if (isTransitioning || actionPending) return
    setActionPending(true)
    try {
      if (isOn) {
        await onStop(service.key)
      } else {
        await onStart(service.key)
      }
    } finally {
      setActionPending(false)
    }
  }

  const handleRestart = async () => {
    if (isTransitioning || actionPending) return
    setActionPending(true)
    try {
      await onRestart(service.key)
    } finally {
      setActionPending(false)
    }
  }

  const handleShowLogs = async () => {
    if (!showLogs) {
      try {
        const data = await getServiceLogs(service.key)
        setLogs(data.logs)
      } catch {
        setLogs('Failed to load logs')
      }
    }
    setShowLogs(!showLogs)
  }

  const uptime = service.started_at
    ? formatUptime(Date.now() / 1000 - service.started_at)
    : null

  const canToggle = depsRunning || isOn

  return (
    <div className={`bg-gray-800 border ${style.border} rounded-xl px-4 py-3 transition-colors`}>
      {/* Header row */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          {isTransitioning ? (
            <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin flex-shrink-0" />
          ) : service.state === 'error' ? (
            <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
          ) : (
            <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${style.dot}`} />
          )}
          <span className="text-sm font-medium">{service.name}</span>
          {service.port && (
            <span className="text-[10px] text-gray-500 bg-gray-700 px-1.5 py-0.5 rounded">:{service.port}</span>
          )}
          {service.is_docker && (
            <span className="text-[10px] text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded">docker</span>
          )}
          {service.restart_count > 0 && (
            <span className="text-[10px] text-orange-400 bg-orange-500/10 px-1.5 py-0.5 rounded">
              {service.restart_count} restart{service.restart_count > 1 ? 's' : ''}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Restart button */}
          {isOn && (
            <button
              onClick={handleRestart}
              disabled={isTransitioning || actionPending}
              className="text-gray-400 hover:text-gray-200 disabled:opacity-40 p-1 rounded transition-colors"
              title="Restart"
            >
              <RotateCw className="w-3.5 h-3.5" />
            </button>
          )}

          {/* Toggle switch */}
          <button
            onClick={handleToggle}
            disabled={isTransitioning || actionPending || (!isOn && !canToggle)}
            title={
              !canToggle && !isOn ? 'Dependencies not running' :
              isTransitioning ? 'Please wait...' :
              isOn ? 'Stop service' : 'Start service'
            }
            className={`
              relative w-10 h-5 rounded-full transition-colors duration-200 flex-shrink-0
              ${isOn ? 'bg-green-600' : 'bg-gray-600'}
              ${(isTransitioning || actionPending || (!isOn && !canToggle)) ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer hover:brightness-110'}
            `}
          >
            <span className={`
              absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200
              ${isOn ? 'translate-x-5' : 'translate-x-0.5'}
            `} />
          </button>
        </div>
      </div>

      {/* Status line */}
      <div className="mt-1.5 ml-5">
        <div className="flex items-center gap-2">
          <span className={`text-xs ${
            service.state === 'running' ? 'text-green-400' :
            service.state === 'error' ? 'text-red-400' :
            service.state === 'starting' ? 'text-blue-400' :
            'text-gray-500'
          }`}>
            {style.label}
          </span>
          {uptime && <span className="text-[11px] text-gray-600">uptime {uptime}</span>}

          {/* Auto-start checkbox */}
          <label className="flex items-center gap-1 ml-auto text-[11px] text-gray-500 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={service.auto_start}
              onChange={e => onAutoStartToggle(service.key, e.target.checked)}
              className="rounded w-3 h-3"
            />
            auto-start
          </label>
        </div>

        {/* Dependency hint */}
        {service.depends_on.length > 0 && !depsRunning && !isOn && (
          <div className="text-[11px] text-yellow-500/70 mt-1">
            Requires: {service.depends_on.join(', ')}
          </div>
        )}

        {/* Error message */}
        {service.state === 'error' && service.error && (
          <div className="mt-2 text-xs text-red-400/80 bg-red-500/5 rounded-lg px-3 py-2 font-mono whitespace-pre-wrap max-h-32 overflow-y-auto">
            {service.error}
          </div>
        )}

        {/* Logs toggle */}
        <button
          onClick={handleShowLogs}
          className="flex items-center gap-1 mt-2 text-[11px] text-gray-500 hover:text-gray-300 transition-colors"
        >
          {showLogs ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {showLogs ? 'Hide logs' : 'Show logs'}
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
