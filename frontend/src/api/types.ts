// Spoke status
export interface SpokeStatus {
  key: string
  name: string
  base_url: string
  online: boolean
  latency_ms: number | null
  error: string | null
}

export interface HealthResponse {
  status: string
  spokes: SpokeStatus[]
}

// Chat
export interface ChatRequest {
  message: string
  conversation_id?: number | null
  profile?: string | null
  provider_id?: number | null
  spokes?: string[] | null
  instruction_id?: number | null
}

export interface ConversationMessage {
  id: number
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string | null
  tool_calls: ToolCallRecord[] | null
  model_profile: string | null
  provider_used: string | null
  created_at: string
}

export interface Conversation {
  id: number
  title: string | null
  model_profile: string | null
  provider_used: string | null
  created_at: string
  updated_at: string
  messages: ConversationMessage[]
}

export interface ConversationListItem {
  id: number
  title: string | null
  model_profile: string | null
  provider_used: string | null
  created_at: string
  updated_at: string
}

// SSE events
export interface ChatSSEEvent {
  type: 'token' | 'tool_call' | 'tool_result' | 'done' | 'error' | 'conversation_id'
  content?: string
  name?: string
  arguments?: Record<string, unknown>
  result?: ToolResult
  id?: number
  conversation_id?: number
}

export interface ToolCallRecord {
  name: string
  arguments: Record<string, unknown>
  result: ToolResult
}

export interface ToolResult {
  success: boolean
  data?: unknown
  error?: string | null
}

// LLM Providers
export interface LLMProvider {
  id: number
  name: string
  provider_type: string
  base_url: string | null
  model_id: string
  enabled: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface LLMProviderCreate {
  name: string
  provider_type: string
  api_key?: string
  base_url?: string
  model_id: string
  enabled?: boolean
  is_default?: boolean
}

// Search
export interface SearchResult {
  source: string
  type: string
  title: string
  snippet: string | null
  url: string | null
  date: string | null
  metadata: Record<string, unknown> | null
}

// Local Model Management (Ollama)
export type ModelState = 'stopped' | 'starting' | 'running' | 'stopping' | 'error'

export interface LocalModel {
  key: string
  name: string
  model_id: string
  vram_gb: number
  context_length: number
  description: string
  default_on: boolean
  state: ModelState
  error: string | null
  started_at: number | null
}

export interface GPUInfo {
  name: string
  total_vram_gb: number
  used_vram_gb: number
  available_vram_gb: number
  estimated_loaded_gb: number
  models_loaded: number
}

export interface ModelActionResult {
  success: boolean
  message: string
  state: ModelState
}

// System Instructions
export interface SystemInstruction {
  id: number
  name: string
  content: string
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface SystemInstructionCreate {
  name: string
  content: string
  is_default?: boolean
}

export interface SystemInstructionUpdate {
  name?: string
  content?: string
  is_default?: boolean
}

// Service Manager
export type ServiceState = 'stopped' | 'starting' | 'running' | 'stopping' | 'error'

export interface ServiceStatus {
  key: string
  name: string
  port: number | null
  state: ServiceState
  error: string | null
  started_at: number | null
  restart_count: number
  auto_start: boolean
  process_group: string
  depends_on: string[]
  is_docker: boolean
}

export interface ServiceActionResult {
  success: boolean
  message: string
  state: ServiceState
}

// Unified people
export interface PersonMapping {
  id: number
  spoke_key: string
  spoke_person_id: string
  spoke_person_name: string | null
}

export interface UnifiedPerson {
  id: number
  display_name: string
  notes: string | null
  created_at: string
  mappings: PersonMapping[]
}
