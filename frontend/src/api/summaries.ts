const BASE = '/api'

export interface SummaryCoverage {
  project: string
  meetings_total: number
  meetings_short: number
  meetings_long: number
  documents_total: number
  documents_short: number
  documents_long: number
}

export interface BatchUploadResult {
  filename: string
  meeting_id: string
  summary_type: string
  success: boolean
  error?: string
}

export interface BatchUploadResponse {
  total: number
  succeeded: number
  failed: number
  results: BatchUploadResult[]
}

export async function getSummaryCoverage(project: string): Promise<SummaryCoverage> {
  const resp = await fetch(`${BASE}/summaries/coverage/${project}`)
  if (!resp.ok) throw new Error(`API error ${resp.status}`)
  return resp.json()
}

export async function batchUploadSummaries(project: string, files: FileList | File[]): Promise<BatchUploadResponse> {
  const fd = new FormData()
  for (const file of files) {
    fd.append('files', file)
  }
  const resp = await fetch(`${BASE}/summaries/batch-upload/${project}`, {
    method: 'POST',
    body: fd,
  })
  if (!resp.ok) throw new Error(`API error ${resp.status}`)
  return resp.json()
}
