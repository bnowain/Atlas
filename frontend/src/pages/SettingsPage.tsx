import { useState, useEffect } from 'react'
import { Plus, Trash2, Check, X, Loader2, Zap } from 'lucide-react'
import { listProviders, createProvider, updateProvider, deleteProvider, testProvider } from '../api/spokes'
import type { LLMProvider } from '../api/types'

export default function SettingsPage() {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [testResults, setTestResults] = useState<Record<number, { success: boolean; error?: string } | 'testing'>>({})

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

  if (loading) return <div className="flex items-center justify-center h-full"><Loader2 className="w-6 h-6 animate-spin text-gray-500" /></div>

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Settings</h1>
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

      {/* Local backends info */}
      <div>
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">Local vLLM Backends</h2>
        <div className="space-y-2">
          {[
            { name: 'atlas-fast', port: 8100, model: 'Qwen2.5-7B-Instruct' },
            { name: 'atlas-quality', port: 8101, model: 'Qwen2.5-72B-Instruct-AWQ' },
            { name: 'atlas-code', port: 8102, model: 'DeepSeek-Coder-V2-Lite' },
          ].map(b => (
            <div key={b.name} className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 flex items-center justify-between">
              <div>
                <div className="text-sm">{b.name}</div>
                <div className="text-xs text-gray-500">{b.model} &middot; port {b.port}</div>
              </div>
              <span className="text-xs text-gray-500">WSL2</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-600 mt-2">
          Start local backends with: <code className="bg-gray-800 px-1 py-0.5 rounded">bash scripts/vllm-start.sh</code> (in WSL2)
        </p>
      </div>
    </div>
  )
}
