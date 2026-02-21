import { useState, useEffect, useCallback } from 'react'
import { listModels, getGPUInfo } from '../api/models'
import type { LocalModel, GPUInfo } from '../api/types'

const POLL_INTERVAL = 5_000

export function useModels() {
  const [models, setModels] = useState<LocalModel[]>([])
  const [gpu, setGpu] = useState<GPUInfo | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const [modelsData, gpuData] = await Promise.all([
        listModels(),
        getGPUInfo(),
      ])
      setModels(modelsData.models)
      setGpu(gpuData)
    } catch {
      // Atlas may be unreachable
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, POLL_INTERVAL)
    return () => clearInterval(timer)
  }, [refresh])

  return { models, gpu, loading, refresh }
}
