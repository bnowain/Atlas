import type { HealthResponse, LLMProvider, LLMProviderCreate, SearchResult, UnifiedPerson } from './types'
import { apiFetch, apiDelete } from './client'

// Health
export function getHealth(): Promise<HealthResponse> {
  return apiFetch('/health')
}

// LLM Providers
export function listProviders(): Promise<LLMProvider[]> {
  return apiFetch('/settings/providers')
}

export function createProvider(data: LLMProviderCreate): Promise<LLMProvider> {
  return apiFetch('/settings/providers', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateProvider(id: number, data: Partial<LLMProviderCreate>): Promise<LLMProvider> {
  return apiFetch(`/settings/providers/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteProvider(id: number): Promise<void> {
  return apiDelete(`/settings/providers/${id}`)
}

export function testProvider(id: number): Promise<{ success: boolean; error?: string; response?: string }> {
  return apiFetch(`/settings/providers/${id}/test`, { method: 'POST' })
}

// Search
export function unifiedSearch(q: string, sources?: string[], limit = 20): Promise<{ results: SearchResult[]; total: number }> {
  const params = new URLSearchParams({ q, limit: String(limit) })
  if (sources?.length) params.set('sources', sources.join(','))
  return apiFetch(`/search?${params}`)
}

// People
export function listPeople(): Promise<UnifiedPerson[]> {
  return apiFetch('/people')
}

export function getPerson(id: number): Promise<UnifiedPerson> {
  return apiFetch(`/people/${id}`)
}

// Spoke proxy helper
export function spokeUrl(spoke: string, path: string): string {
  return `/api/spokes/${spoke}/${path.replace(/^\//, '')}`
}
