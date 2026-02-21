import { useState, useEffect, useRef } from 'react'
import { ChevronDown, ScrollText, Plus, Pencil, Trash2, Loader2, Star } from 'lucide-react'
import { listInstructions, createInstruction, updateInstruction, deleteInstruction } from '../../api/instructions'
import type { SystemInstruction } from '../../api/types'

interface InstructionSelectorProps {
  selectedInstructionId: number | null
  onSelect: (id: number | null) => void
}

export default function InstructionSelector({
  selectedInstructionId,
  onSelect,
}: InstructionSelectorProps) {
  const [open, setOpen] = useState(false)
  const [instructions, setInstructions] = useState<SystemInstruction[]>([])
  const [editing, setEditing] = useState<number | null>(null) // instruction id being edited
  const [adding, setAdding] = useState(false)
  const [formName, setFormName] = useState('')
  const [formContent, setFormContent] = useState('')
  const [formDefault, setFormDefault] = useState(false)
  const [saving, setSaving] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const fetchInstructions = () => {
    listInstructions().then(setInstructions).catch(() => {})
  }

  useEffect(() => {
    fetchInstructions()
  }, [])

  // Re-fetch when dropdown opens
  useEffect(() => {
    if (open) fetchInstructions()
  }, [open])

  // Click-outside handler
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
        setAdding(false)
        setEditing(null)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const selectedInstruction = instructions.find(i => i.id === selectedInstructionId)

  const startAdding = () => {
    setAdding(true)
    setEditing(null)
    setFormName('')
    setFormContent('')
    setFormDefault(false)
  }

  const startEditing = (inst: SystemInstruction) => {
    setEditing(inst.id)
    setAdding(false)
    setFormName(inst.name)
    setFormContent(inst.content)
    setFormDefault(inst.is_default)
  }

  const cancelForm = () => {
    setAdding(false)
    setEditing(null)
  }

  const handleSave = async () => {
    if (!formName.trim() || !formContent.trim()) return
    setSaving(true)
    try {
      if (editing) {
        const updated = await updateInstruction(editing, {
          name: formName,
          content: formContent,
          is_default: formDefault,
        })
        setInstructions(prev => prev.map(i => i.id === updated.id ? updated : (formDefault ? { ...i, is_default: false } : i)))
      } else {
        const created = await createInstruction({
          name: formName,
          content: formContent,
          is_default: formDefault,
        })
        setInstructions(prev => formDefault ? [...prev.map(i => ({ ...i, is_default: false })), created] : [...prev, created])
        onSelect(created.id)
      }
      cancelForm()
      fetchInstructions()
    } catch {
      // leave form open
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await deleteInstruction(id)
      setInstructions(prev => prev.filter(i => i.id !== id))
      if (selectedInstructionId === id) onSelect(null)
    } catch {
      // ignore
    }
  }

  return (
    <div className="relative" ref={ref}>
      {/* Trigger */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg px-3 py-1.5 text-xs transition-colors"
      >
        <ScrollText className="w-3.5 h-3.5 text-gray-400" />
        <span className="truncate max-w-[140px]">
          {selectedInstruction ? selectedInstruction.name : 'No instructions'}
        </span>
        <ChevronDown className={`w-3 h-3 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full left-0 mt-1 bg-gray-800 border border-gray-700 rounded-xl shadow-xl z-50 w-80 overflow-hidden">
          {/* None option */}
          <button
            onClick={() => { onSelect(null); setOpen(false) }}
            className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-700 transition-colors ${
              !selectedInstructionId ? 'bg-gray-700/50' : ''
            }`}
          >
            <span className="text-gray-400">None</span>
          </button>

          {/* Instruction list */}
          {instructions.map(inst => (
            <div key={inst.id}>
              {editing === inst.id ? (
                /* Inline edit form */
                <div className="px-3 py-2 space-y-2 border-t border-gray-700/50">
                  <div className="text-xs text-gray-400 font-medium">Edit instruction</div>
                  <input
                    value={formName}
                    onChange={e => setFormName(e.target.value)}
                    placeholder="Name"
                    className="w-full bg-gray-900 border border-gray-600 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-blue-500"
                    autoFocus
                  />
                  <textarea
                    value={formContent}
                    onChange={e => setFormContent(e.target.value)}
                    placeholder="Instructions for the AI..."
                    rows={4}
                    className="w-full bg-gray-900 border border-gray-600 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-blue-500 resize-y"
                  />
                  <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formDefault}
                      onChange={e => setFormDefault(e.target.checked)}
                      className="rounded border-gray-600"
                    />
                    Set as default
                  </label>
                  <div className="flex gap-2 justify-end">
                    <button onClick={cancelForm} className="text-xs text-gray-400 hover:text-gray-200 px-2 py-1">
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={!formName.trim() || !formContent.trim() || saving}
                      className="text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-3 py-1 rounded-lg transition-colors flex items-center gap-1"
                    >
                      {saving && <Loader2 className="w-3 h-3 animate-spin" />}
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                /* Instruction row */
                <button
                  onClick={() => { onSelect(inst.id); setOpen(false) }}
                  className={`w-full text-left px-3 py-2 flex items-center gap-2 text-sm hover:bg-gray-700 transition-colors group ${
                    selectedInstructionId === inst.id ? 'bg-gray-700/50' : ''
                  }`}
                >
                  <ScrollText className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="truncate flex items-center gap-1.5">
                      {inst.name}
                      {inst.is_default && <Star className="w-3 h-3 text-yellow-500 fill-yellow-500 flex-shrink-0" />}
                    </div>
                    <div className="text-[11px] text-gray-500 truncate">{inst.content.slice(0, 60)}...</div>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                    <button
                      onClick={e => { e.stopPropagation(); startEditing(inst) }}
                      className="p-1 hover:text-blue-400 transition-colors"
                    >
                      <Pencil className="w-3 h-3" />
                    </button>
                    <button
                      onClick={e => handleDelete(inst.id, e)}
                      className="p-1 hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </button>
              )}
            </div>
          ))}

          {/* Add new */}
          {adding ? (
            <div className="px-3 py-2 space-y-2 border-t border-gray-700/50">
              <div className="text-xs text-gray-400 font-medium">New instruction</div>
              <input
                value={formName}
                onChange={e => setFormName(e.target.value)}
                placeholder="Name"
                className="w-full bg-gray-900 border border-gray-600 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-blue-500"
                autoFocus
              />
              <textarea
                value={formContent}
                onChange={e => setFormContent(e.target.value)}
                placeholder="Instructions for the AI..."
                rows={4}
                className="w-full bg-gray-900 border border-gray-600 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-blue-500 resize-y"
              />
              <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formDefault}
                  onChange={e => setFormDefault(e.target.checked)}
                  className="rounded border-gray-600"
                />
                Set as default
              </label>
              <div className="flex gap-2 justify-end">
                <button onClick={cancelForm} className="text-xs text-gray-400 hover:text-gray-200 px-2 py-1">
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={!formName.trim() || !formContent.trim() || saving}
                  className="text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-3 py-1 rounded-lg transition-colors flex items-center gap-1"
                >
                  {saving && <Loader2 className="w-3 h-3 animate-spin" />}
                  Save
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={startAdding}
              className="w-full text-left px-3 py-2 flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors border-t border-gray-700/50"
            >
              <Plus className="w-3.5 h-3.5 flex-shrink-0" />
              <span>Add instruction...</span>
            </button>
          )}
        </div>
      )}
    </div>
  )
}
