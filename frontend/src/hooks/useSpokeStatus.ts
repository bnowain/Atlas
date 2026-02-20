import { useState, useEffect, useCallback } from 'react'
import { getHealth } from '../api/spokes'
import type { SpokeStatus } from '../api/types'

const POLL_INTERVAL = 30_000

export function useSpokeStatus() {
  const [spokes, setSpokes] = useState<SpokeStatus[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const data = await getHealth()
      setSpokes(data.spokes)
    } catch {
      // Atlas itself might be down
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, POLL_INTERVAL)
    return () => clearInterval(timer)
  }, [refresh])

  return { spokes, loading, refresh }
}
