import type { ServiceStatus, ServiceActionResult } from './types'
import { apiFetch } from './client'

export function listServices(): Promise<{ services: ServiceStatus[] }> {
  return apiFetch('/services')
}

export function startService(key: string): Promise<ServiceActionResult> {
  return apiFetch(`/services/${key}/start`, { method: 'POST' })
}

export function stopService(key: string): Promise<ServiceActionResult> {
  return apiFetch(`/services/${key}/stop`, { method: 'POST' })
}

export function restartService(key: string): Promise<ServiceActionResult> {
  return apiFetch(`/services/${key}/restart`, { method: 'POST' })
}

export function getServiceLogs(key: string, lines = 100): Promise<{ key: string; logs: string }> {
  return apiFetch(`/services/${key}/logs?lines=${lines}`)
}

export function updateAutoStart(key: string, enabled: boolean): Promise<{ key: string; auto_start: boolean }> {
  return apiFetch(`/services/${key}/auto-start?enabled=${enabled}`, { method: 'PATCH' })
}

export function startAllServices(): Promise<{ results: Array<{ key: string; success: boolean; message: string }> }> {
  return apiFetch('/services/start-all', { method: 'POST' })
}

export function stopAllServices(): Promise<{ results: Array<{ key: string; success: boolean; message: string }> }> {
  return apiFetch('/services/stop-all', { method: 'POST' })
}
