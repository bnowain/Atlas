import { useState, useEffect } from 'react'

export interface ResultItem {
  id: string
  source: string        // spoke key e.g. 'civic_media'
  type: string          // 'video' | 'audio' | 'document' | 'text' | 'article' | 'message' | 'vote'
  title: string
  snippet: string | null
  date: string | null
  thumbnailUrl: string | null
  url: string           // Internal route or external URL
  relevanceScore: number | null
  metadata: Record<string, unknown>
}

interface ResultsState {
  items: ResultItem[]
  query: string
}

let _state: ResultsState = { items: [], query: '' }
const _listeners = new Set<() => void>()

function _notify() {
  _listeners.forEach(fn => fn())
}

export function setResults(items: ResultItem[], query: string) {
  _state = { items, query }
  _notify()
}

export function getResults(): ResultsState {
  return _state
}

export function useResults(): ResultsState {
  const [, forceUpdate] = useState(0)

  useEffect(() => {
    const listener = () => forceUpdate(n => n + 1)
    _listeners.add(listener)
    return () => { _listeners.delete(listener) }
  }, [])

  return _state
}
