import { useState, useEffect, useMemo, useRef } from 'react'
import { Plus, Trash2, Check, X, Loader2, Zap, Play, Square, Upload, FileText } from 'lucide-react'
import SystemPromptEditor from '../components/Chat/SystemPromptEditor'
import { listProviders, createProvider, updateProvider, deleteProvider, testProvider } from '../api/spokes'
import { startModel, stopModel } from '../api/models'
import { startService, stopService, restartService, updateAutoStart, startAllServices, stopAllServices } from '../api/services'
import { getSummaryCoverage, batchUploadSummaries } from '../api/summaries'
import type { SummaryCoverage, BatchUploadResponse } from '../api/summaries'
import { useModels } from '../hooks/useModels'
import { useServices } from '../hooks/useServices'
import type { LLMProvider } from '../api/types'
import VRAMBar from '../components/Settings/VRAMBar'
import ModelCard from '../components/Settings/ModelCard'
import ServiceCard from '../components/Settings/ServiceCard'

export default function SettingsPage() {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [testResults, setTestResults] = useState<Record<number, { success: boolean; error?: string } | 'testing'>>({})
  const [bulkAction, setBulkAction] = useState(false)

  // vLLM models
  const { models, gpu, refresh: refreshModels } = useModels()
  // Spoke services
  const { services, refresh: refreshServices } = useServices()

  // Group services by process_group
  const serviceGroups = useMemo(() => {
    const groups: Record<string, typeof services> = {}
    for (const s of services) {
      const group = s.process_group || 'Other'
      if (!groups[group]) groups[group] = []
      groups[group].push(s)
    }
    return groups
  }, [services])

  // Running services set (for dependency checking)
  const runningKeys = useMemo(() => new Set(
    services.filter(s => s.state === 'running').map(s => s.key)
  ), [services])

  const handleStartService = async (key: string) => {
    await startService(key)
    refreshServices()
  }

  const handleStopService = async (key: string) => {
    await stopService(key)
    refreshServices()
  }

  const handleRestartService = async (key: string) => {
    await restartService(key)
    refreshServices()
  }

  const handleAutoStartToggle = async (key: string, enabled: boolean) => {
    await updateAutoStart(key, enabled)
    refreshServices()
  }

  const handleStartAll = async () => {
    setBulkAction(true)
    try {
      await startAllServices()
      refreshServices()
    } finally {
      setBulkAction(false)
    }
  }

  const handleStopAll = async () => {
    setBulkAction(true)
    try {
      await stopAllServices()
      refreshServices()
    } finally {
      setBulkAction(false)
    }
  }

  const handleStartModel = async (key: string) => {
    await startModel(key)
    refreshModels()
  }

  const handleStopModel = async (key: string) => {
    await stopModel(key)
    refreshModels()
  }

  // Summary Management state
  const [summaryProject, setSummaryProject] = useState('civic_media')
  const [coverage, setCoverage] = useState<SummaryCoverage | null>(null)
  const [coverageLoading, setCoverageLoading] = useState(false)
  const [uploadResult, setUploadResult] = useState<BatchUploadResponse | null>(null)
  const [uploading, setUploading] = useState(false)
  const summaryFileRef = useRef<HTMLInputElement>(null)

  const loadCoverage = async (project: string) => {
    setCoverageLoading(true)
    setCoverage(null)
    try {
      const data = await getSummaryCoverage(project)
      setCoverage(data)
    } catch {
      setCoverage(null)
    } finally {
      setCoverageLoading(false)
    }
  }

  const handleBatchUpload = async (files: FileList) => {
    setUploading(true)
    setUploadResult(null)
    try {
      const result = await batchUploadSummaries(summaryProject, files)
      setUploadResult(result)
      loadCoverage(summaryProject)
    } catch (e: any) {
      setUploadResult({ total: 0, succeeded: 0, failed: 0, results: [{ filename: '', meeting_id: '', summary_type: '', success: false, error: e.message }] })
    } finally {
      setUploading(false)
    }
  }

  // Form state
  const [form, setForm] = useState({
    name: '',
    provider_type: 'openai',
    api_key: '',
    base_url: '',
    model_id: '',
    is_default: false,
  })

  useEffect(() => {
    listProviders()
      .then(setProviders)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleAdd = async () => {
    const provider = await createProvider({
      name: form.name,
      provider_type: form.provider_type,
      api_key: form.api_key || undefined,
      base_url: form.base_url || undefined,
      model_id: form.model_id,
      is_default: form.is_default,
    })
    setProviders(prev => [...prev, provider])
    setShowAdd(false)
    setForm({ name: '', provider_type: 'openai', api_key: '', base_url: '', model_id: '', is_default: false })
  }

  const handleToggle = async (id: number, enabled: boolean) => {
    const updated = await updateProvider(id, { enabled })
    setProviders(prev => prev.map(p => p.id === id ? updated : p))
  }

  const handleSetDefault = async (id: number) => {
    const updated = await updateProvider(id, { is_default: true })
    // Refresh all to clear old default
    const all = await listProviders()
    setProviders(all)
  }

  const handleDelete = async (id: number) => {
    await deleteProvider(id)
    setProviders(prev => prev.filter(p => p.id !== id))
  }

  const handleTest = async (id: number) => {
    setTestResults(prev => ({ ...prev, [id]: 'testing' }))
    const result = await testProvider(id)
    setTestResults(prev => ({ ...prev, [id]: result }))
  }

  const providerTypes = [
    { value: 'openai', label: 'OpenAI', defaultUrl: 'https://api.openai.com/v1', defaultModel: 'gpt-4o' },
    { value: 'claude', label: 'Claude (Anthropic)', defaultUrl: '', defaultModel: 'claude-sonnet-4-20250514' },
    { value: 'deepseek', label: 'DeepSeek', defaultUrl: 'https://api.deepseek.com/v1', defaultModel: 'deepseek-chat' },
  ]

  // Summary counts
  const runningCount = services.filter(s => s.state === 'running').length
  const totalCount = services.length

  if (loading) return <div className="flex items-center justify-center h-full"><Loader2 className="w-6 h-6 animate-spin text-gray-500" /></div>

  return (
    <div className="max-w-3xl mx-auto px-3 md:px-6 py-4 md:py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Settings</h1>
      </div>

      {/* Base System Prompt */}
      <div className="mb-8">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-1">Base System Prompt</h2>
        <p className="text-xs text-gray-500 mb-3">
          The instructions Atlas uses on every tool-enabled chat. Changes take effect on the next message.
        </p>
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <SystemPromptEditor />
        </div>
      </div>

      {/* Spoke Services */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">Spoke Services</h2>
            <span className="text-xs text-gray-500">
              {runningCount}/{totalCount} running
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleStartAll}
              disabled={bulkAction}
              className="flex items-center gap-1 text-xs bg-green-700 hover:bg-green-600 disabled:opacity-40 px-3 py-1.5 rounded-lg transition-colors"
            >
              {bulkAction ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
              Start All
            </button>
            <button
              onClick={handleStopAll}
              disabled={bulkAction}
              className="flex items-center gap-1 text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-40 px-3 py-1.5 rounded-lg transition-colors"
            >
              {bulkAction ? <Loader2 className="w-3 h-3 animate-spin" /> : <Square className="w-3 h-3" />}
              Stop All
            </button>
          </div>
        </div>

        <p className="text-xs text-gray-500 mb-4">
          Start, stop, and monitor spoke services. Services auto-restart on failure (max 3 in 10 min).
        </p>

        {Object.entries(serviceGroups).map(([group, groupServices]) => (
          <div key={group} className="mb-4">
            <h3 className="text-xs font-medium text-gray-500 mb-2 pl-1">{group}</h3>
            <div className="space-y-2">
              {groupServices.map(s => {
                const depsRunning = s.depends_on.every(dep => runningKeys.has(dep))
                return (
                  <ServiceCard
                    key={s.key}
                    service={s}
                    onStart={handleStartService}
                    onStop={handleStopService}
                    onRestart={handleRestartService}
                    onAutoStartToggle={handleAutoStartToggle}
                    depsRunning={depsRunning}
                  />
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Summary Management */}
      <div className="mb-8">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">Summary Management</h2>
        <p className="text-xs text-gray-500 mb-4">
          Batch upload markdown summaries to spoke projects. File naming: <code className="bg-gray-800 px-1 rounded">{'{meeting_id}_short.md'}</code> or <code className="bg-gray-800 px-1 rounded">{'{meeting_id}_long.md'}</code>
        </p>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-3">
            <label className="text-xs text-gray-400">Project:</label>
            <select
              value={summaryProject}
              onChange={e => { setSummaryProject(e.target.value); setCoverage(null); setUploadResult(null) }}
              className="bg-gray-900 border border-gray-600 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500"
            >
              <option value="civic_media">civic_media</option>
            </select>
            <button
              onClick={() => loadCoverage(summaryProject)}
              disabled={coverageLoading}
              className="flex items-center gap-1 text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-40 px-3 py-1.5 rounded-lg transition-colors"
            >
              {coverageLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
              Check Coverage
            </button>
          </div>

          {coverage && (
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-gray-900 rounded-lg p-3">
                <div className="text-gray-400 mb-1">Meetings</div>
                <div>{coverage.meetings_short}/{coverage.meetings_total} have short summary</div>
                <div>{coverage.meetings_long}/{coverage.meetings_total} have long summary</div>
              </div>
              <div className="bg-gray-900 rounded-lg p-3">
                <div className="text-gray-400 mb-1">Documents</div>
                <div>{coverage.documents_short}/{coverage.documents_total} have short summary</div>
                <div>{coverage.documents_long}/{coverage.documents_total} have long summary</div>
              </div>
            </div>
          )}

          <div className="flex items-center gap-3">
            <input
              ref={summaryFileRef}
              type="file"
              accept=".md,.txt"
              multiple
              className="hidden"
              onChange={e => { if (e.target.files?.length) handleBatchUpload(e.target.files); e.target.value = '' }}
            />
            <button
              onClick={() => summaryFileRef.current?.click()}
              disabled={uploading}
              className="flex items-center gap-1 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-3 py-1.5 rounded-lg transition-colors"
            >
              {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
              {uploading ? 'Uploading…' : 'Upload .md Files'}
            </button>
          </div>

          {uploadResult && (
            <div className="text-xs space-y-1">
              <div className={uploadResult.failed > 0 ? 'text-yellow-400' : 'text-green-400'}>
                {uploadResult.succeeded} succeeded, {uploadResult.failed} failed ({uploadResult.total} total)
              </div>
              {uploadResult.results.filter(r => !r.success).map((r, i) => (
                <div key={i} className="text-red-400 pl-2">
                  {r.filename}: {r.error}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* LLM Providers */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">LLM Providers</h2>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-1 text-xs bg-blue-600 hover:bg-blue-500 px-3 py-1.5 rounded-lg transition-colors"
          >
            <Plus className="w-3 h-3" /> Add Provider
          </button>
        </div>

        <p className="text-xs text-gray-500 mb-4">
          Configure external LLM APIs as alternatives to local vLLM backends. API keys are encrypted at rest.
        </p>

        {/* Add form */}
        {showAdd && (
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 mb-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Name</label>
                <input
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder="My OpenAI"
                  className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Provider Type</label>
                <select
                  value={form.provider_type}
                  onChange={e => {
                    const pt = providerTypes.find(p => p.value === e.target.value)
                    setForm({
                      ...form,
                      provider_type: e.target.value,
                      base_url: pt?.defaultUrl || '',
                      model_id: pt?.defaultModel || '',
                    })
                  }}
                  className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
                >
                  {providerTypes.map(pt => (
                    <option key={pt.value} value={pt.value}>{pt.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">API Key</label>
              <input
                type="password"
                value={form.api_key}
                onChange={e => setForm({ ...form, api_key: e.target.value })}
                placeholder="sk-..."
                className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Base URL</label>
                <input
                  value={form.base_url}
                  onChange={e => setForm({ ...form, base_url: e.target.value })}
                  placeholder="https://api.openai.com/v1"
                  className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Model ID</label>
                <input
                  value={form.model_id}
                  onChange={e => setForm({ ...form, model_id: e.target.value })}
                  placeholder="gpt-4o"
                  className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
                />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_default}
                  onChange={e => setForm({ ...form, is_default: e.target.checked })}
                  className="rounded"
                />
                Set as default provider
              </label>
              <div className="flex gap-2">
                <button onClick={() => setShowAdd(false)} className="text-xs text-gray-400 hover:text-gray-200 px-3 py-1.5">Cancel</button>
                <button
                  onClick={handleAdd}
                  disabled={!form.name || !form.model_id}
                  className="text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-3 py-1.5 rounded-lg transition-colors"
                >
                  Add
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Provider list */}
        {providers.length === 0 && !showAdd && (
          <div className="text-gray-500 text-sm">No external providers configured. Using local vLLM backends.</div>
        )}

        <div className="space-y-2">
          {providers.map(p => {
            const test = testResults[p.id]
            return (
              <div key={p.id} className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium ${p.enabled ? '' : 'text-gray-500'}`}>{p.name}</span>
                    <span className="text-xs text-gray-500 bg-gray-700 px-1.5 py-0.5 rounded">{p.provider_type}</span>
                    {p.is_default && <span className="text-xs text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">Default</span>}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handleTest(p.id)}
                      className="text-xs text-gray-400 hover:text-gray-200 px-2 py-1 hover:bg-gray-700 rounded transition-colors"
                      title="Test connection"
                    >
                      {test === 'testing' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
                    </button>
                    {!p.is_default && (
                      <button
                        onClick={() => handleSetDefault(p.id)}
                        className="text-xs text-gray-400 hover:text-blue-400 px-2 py-1 hover:bg-gray-700 rounded transition-colors"
                        title="Set as default"
                      >
                        <Check className="w-3 h-3" />
                      </button>
                    )}
                    <button
                      onClick={() => handleToggle(p.id, !p.enabled)}
                      className={`text-xs px-2 py-1 rounded transition-colors ${
                        p.enabled ? 'text-green-400 hover:bg-gray-700' : 'text-gray-500 hover:bg-gray-700'
                      }`}
                    >
                      {p.enabled ? 'On' : 'Off'}
                    </button>
                    <button
                      onClick={() => handleDelete(p.id)}
                      className="text-xs text-gray-400 hover:text-red-400 px-2 py-1 hover:bg-gray-700 rounded transition-colors"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-1">{p.model_id}</div>

                {/* Test result */}
                {test && test !== 'testing' && (
                  <div className={`text-xs mt-2 ${test.success ? 'text-green-400' : 'text-red-400'}`}>
                    {test.success ? 'Connection successful' : `Error: ${test.error}`}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Local Ollama Backends */}
      <div>
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">Local Ollama Models</h2>
        <p className="text-xs text-gray-500 mb-4">
          GPU-accelerated models via Ollama. Toggle models on and off — VRAM is tracked automatically.
        </p>

        {gpu && <VRAMBar gpu={gpu} />}

        <div className="space-y-2">
          {models.map(m => (
            <ModelCard
              key={m.key}
              model={m}
              onStart={handleStartModel}
              onStop={handleStopModel}
              canLoad={gpu ? gpu.available_vram_gb >= m.vram_gb : true}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
