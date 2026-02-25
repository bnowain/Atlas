import { apiFetch } from './client'

export interface SystemPromptData {
  id: number
  content: string
  updated_at: string
}

export async function getSystemPrompt(): Promise<SystemPromptData> {
  return apiFetch<SystemPromptData>('/system-prompt')
}

export async function updateSystemPrompt(content: string): Promise<SystemPromptData> {
  return apiFetch<SystemPromptData>('/system-prompt', {
    method: 'PUT',
    body: JSON.stringify({ content }),
  })
}
