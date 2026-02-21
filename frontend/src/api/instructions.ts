import type { SystemInstruction, SystemInstructionCreate, SystemInstructionUpdate } from './types'
import { apiFetch, apiDelete } from './client'

export function listInstructions(): Promise<SystemInstruction[]> {
  return apiFetch('/instructions')
}

export function getDefaultInstruction(): Promise<SystemInstruction | null> {
  return apiFetch('/instructions/default')
}

export function createInstruction(data: SystemInstructionCreate): Promise<SystemInstruction> {
  return apiFetch('/instructions', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateInstruction(id: number, data: SystemInstructionUpdate): Promise<SystemInstruction> {
  return apiFetch(`/instructions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteInstruction(id: number): Promise<void> {
  return apiDelete(`/instructions/${id}`)
}
