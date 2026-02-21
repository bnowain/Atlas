import { useState, useEffect, useRef } from 'react'
import { ChevronDown, Cloud, Plus, Loader2 } from 'lucide-react'
import { useModels } from '../../hooks/useModels'
import { listProviders, createProvider } from '../../api/spokes'
import type { LLMProvider } from '../../api/types'

interface ModelSelectorProps {
  selectedProfile: string | null
  selectedProviderId: number | null
  onSelectLocal: (profile: string) => void
  onSelectProvider: (providerId: number) => void
  onProviderCreated: () => void
}

const CLOUD_TYPES = [
  { type: 'openai', label: 'OpenAI', defaultModel: 'gpt-4o', placeholder: 'sk-...' },
  { type: 'claude', label: 'Anthropic', defaultModel: 'claude-sonnet-4-20250514', placeholder: 'sk-ant-...' },
] as const

export default function ModelSelector({
  selectedProfile,
  selectedProviderId,
  onSelectLocal,
  onSelectProvider,
  onProviderCreated,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false)
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [addingType, setAddingType] = useState<string | null>(null)
  const [formData, setFormData] = useState({ name: '', api_key: '', model_id: '' })
  const [saving, setSaving] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const { models } = useModels()

  // Fetch providers on mount & when dropdown opens
  useEffect(() => {
    listProviders().then(setProviders).catch(() => {})
  }, [open])

  // Click-outside handler
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
        setAddingType(null)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Derive display label
  const getLabel = (): string => {
    if (selectedProfile) {
      const m = models.find(m => m.key === selectedProfile)
      return m ? m.name : selectedProfile
    }
    if (selectedProviderId) {
      const p = providers.find(p => p.id === selectedProviderId)
      return p ? `${p.name}` : `Provider #${selectedProviderId}`
    }
    return 'Select model'
  }

  const enabledProviders = providers.filter(p => p.enabled)

  // Which cloud types already have providers configured
  const configuredTypes = new Set(enabledProviders.map(p => p.provider_type))

  const handleAddProvider = async () => {
    if (!addingType || !formData.name || !formData.api_key || !formData.model_id) return
    setSaving(true)
    try {
      const provider = await createProvider({
        name: formData.name,
        provider_type: addingType,
        api_key: formData.api_key,
        model_id: formData.model_id,
        enabled: true,
      })
      setProviders(prev => [...prev, provider])
      onSelectProvider(provider.id)
      onProviderCreated()
      setAddingType(null)
      setFormData({ name: '', api_key: '', model_id: '' })
      setOpen(false)
    } catch {
      // leave form open on error
    } finally {
      setSaving(false)
    }
  }

  const startAdding = (type: string) => {
    const ct = CLOUD_TYPES.find(c => c.type === type)
    setAddingType(type)
    setFormData({
      name: `My ${ct?.label || type}`,
      api_key: '',
      model_id: ct?.defaultModel || '',
    })
  }

  return (
    <div className="relative" ref={ref}>
      {/* Trigger */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg px-3 py-1.5 text-xs transition-colors"
      >
        <span className="truncate max-w-[140px]">{getLabel()}</span>
        <ChevronDown className={`w-3 h-3 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full left-0 mt-1 bg-gray-800 border border-gray-700 rounded-xl shadow-xl z-50 w-72 overflow-hidden">
          {/* Local Models */}
          {models.length > 0 && (
            <>
              <div className="text-[11px] text-gray-500 uppercase tracking-wide px-3 pt-2.5 pb-1">Local</div>
              {models.map(m => {
                const isRunning = m.state === 'running'
                const isSelected = selectedProfile === m.key
                return (
                  <button
                    key={m.key}
                    onClick={() => {
                      if (isRunning) {
                        onSelectLocal(m.key)
                        setOpen(false)
                      }
                    }}
                    disabled={!isRunning}
                    className={`w-full text-left px-3 py-2 flex items-center gap-2 text-sm transition-colors ${
                      isSelected ? 'bg-gray-700/50' : ''
                    } ${isRunning ? 'hover:bg-gray-700 cursor-pointer' : 'opacity-40 cursor-default'}`}
                  >
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${isRunning ? 'bg-green-400' : 'bg-gray-600'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="truncate">{m.name}</div>
                      <div className="text-[11px] text-gray-500 truncate">
                        {isRunning ? m.description : 'Not loaded — start in Settings'}
                      </div>
                    </div>
                  </button>
                )
              })}
            </>
          )}

          {/* Cloud Providers */}
          {(enabledProviders.length > 0 || CLOUD_TYPES.length > 0) && (
            <>
              <div className="border-t border-gray-700 mt-1" />
              <div className="text-[11px] text-gray-500 uppercase tracking-wide px-3 pt-2.5 pb-1">Cloud</div>

              {enabledProviders.map(p => {
                const isSelected = selectedProviderId === p.id
                return (
                  <button
                    key={p.id}
                    onClick={() => {
                      onSelectProvider(p.id)
                      setOpen(false)
                    }}
                    className={`w-full text-left px-3 py-2 flex items-center gap-2 text-sm hover:bg-gray-700 cursor-pointer transition-colors ${
                      isSelected ? 'bg-gray-700/50' : ''
                    }`}
                  >
                    <Cloud className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="truncate">{p.name}</div>
                      <div className="text-[11px] text-gray-500 truncate">{p.model_id}</div>
                    </div>
                  </button>
                )
              })}

              {/* Add provider buttons */}
              {CLOUD_TYPES.filter(ct => !configuredTypes.has(ct.type)).map(ct => (
                <div key={ct.type}>
                  {addingType === ct.type ? (
                    <div className="px-3 py-2 space-y-2 border-t border-gray-700/50">
                      <div className="text-xs text-gray-400 font-medium">Add {ct.label}</div>
                      <input
                        value={formData.name}
                        onChange={e => setFormData(d => ({ ...d, name: e.target.value }))}
                        placeholder="Name"
                        className="w-full bg-gray-900 border border-gray-600 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-blue-500"
                        autoFocus
                      />
                      <input
                        type="password"
                        value={formData.api_key}
                        onChange={e => setFormData(d => ({ ...d, api_key: e.target.value }))}
                        placeholder={ct.placeholder}
                        className="w-full bg-gray-900 border border-gray-600 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-blue-500"
                      />
                      <input
                        value={formData.model_id}
                        onChange={e => setFormData(d => ({ ...d, model_id: e.target.value }))}
                        placeholder="Model ID"
                        className="w-full bg-gray-900 border border-gray-600 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-blue-500"
                      />
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => setAddingType(null)}
                          className="text-xs text-gray-400 hover:text-gray-200 px-2 py-1"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleAddProvider}
                          disabled={!formData.api_key || !formData.model_id || saving}
                          className="text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-3 py-1 rounded-lg transition-colors flex items-center gap-1"
                        >
                          {saving && <Loader2 className="w-3 h-3 animate-spin" />}
                          Save
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => startAdding(ct.type)}
                      className="w-full text-left px-3 py-2 flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5 flex-shrink-0" />
                      <span>Add {ct.label}...</span>
                    </button>
                  )}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}
