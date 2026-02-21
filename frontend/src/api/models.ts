import type { LocalModel, GPUInfo, ModelActionResult } from './types'
import { apiFetch } from './client'

export function listModels(): Promise<{ models: LocalModel[] }> {
  return apiFetch('/models')
}

export function getGPUInfo(): Promise<GPUInfo> {
  return apiFetch('/models/gpu')
}

export function startModel(key: string): Promise<ModelActionResult> {
  return apiFetch(`/models/${key}/start`, { method: 'POST' })
}

export function stopModel(key: string): Promise<ModelActionResult> {
  return apiFetch(`/models/${key}/stop`, { method: 'POST' })
}

export function getModelLogs(key: string, lines = 50): Promise<{ key: string; logs: string }> {
  return apiFetch(`/models/${key}/logs?lines=${lines}`)
}
