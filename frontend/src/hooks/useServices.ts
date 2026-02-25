import { useState, useEffect, useCallback } from 'react'
import { listServices } from '../api/services'
import type { ServiceStatus } from '../api/types'

const POLL_INTERVAL = 5_000

export function useServices() {
  const [services, setServices] = useState<ServiceStatus[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const data = await listServices()
      setServices(data.services)
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

  return { services, loading, refresh }
}
