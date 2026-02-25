export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return formatDate(iso)
}

export function spokeLabel(key: string): string {
  const labels: Record<string, string> = {
    civic_media: 'Civic Media',
    article_tracker: 'Article Tracker',
    shasta_db: 'Shasta-DB',
    facebook_offline: 'Facebook',
    shasta_pra: 'Shasta PRA',
    facebook_monitor: 'FB Monitor',
    campaign_finance: 'Campaign Finance',
  }
  return labels[key] || key
}

export function spokeColor(key: string): string {
  const colors: Record<string, string> = {
    civic_media: 'text-blue-400',
    article_tracker: 'text-amber-400',
    shasta_db: 'text-emerald-400',
    facebook_offline: 'text-purple-400',
    shasta_pra: 'text-sky-400',
    facebook_monitor: 'text-violet-400',
    campaign_finance: 'text-orange-400',
  }
  return colors[key] || 'text-gray-400'
}

export function spokeBg(key: string): string {
  const colors: Record<string, string> = {
    civic_media: 'bg-blue-500/10 border-blue-500/20',
    article_tracker: 'bg-amber-500/10 border-amber-500/20',
    shasta_db: 'bg-emerald-500/10 border-emerald-500/20',
    facebook_offline: 'bg-purple-500/10 border-purple-500/20',
    shasta_pra: 'bg-sky-500/10 border-sky-500/20',
    facebook_monitor: 'bg-violet-500/10 border-violet-500/20',
    campaign_finance: 'bg-orange-500/10 border-orange-500/20',
  }
  return colors[key] || 'bg-gray-500/10 border-gray-500/20'
}
