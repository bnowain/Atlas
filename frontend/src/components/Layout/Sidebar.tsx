import { NavLink } from 'react-router-dom'
import { useSpokeStatus } from '../../hooks/useSpokeStatus'
import {
  LayoutDashboard, MessageSquare, Search, Users,
  Video, Newspaper, Archive, Mail, Settings, Globe,
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/search', label: 'Search', icon: Search },
  { type: 'divider' as const },
  { to: '/meetings', label: 'Meetings', icon: Video, spoke: 'civic_media' },
  { to: '/articles', label: 'Articles', icon: Newspaper, spoke: 'article_tracker' },
  { to: '/files', label: 'Files', icon: Archive, spoke: 'shasta_db' },
  { to: '/messages', label: 'Messages', icon: Mail, spoke: 'facebook_offline' },
  { type: 'divider' as const },
  { to: '/people', label: 'People', icon: Users },
  { type: 'divider' as const },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const

interface SidebarProps {
  onNavigate?: () => void
}

export default function Sidebar({ onNavigate }: SidebarProps) {
  const { spokes } = useSpokeStatus()
  const spokeMap = Object.fromEntries(spokes.map(s => [s.key, s]))

  return (
    <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col h-full shrink-0">
      {/* Logo — hidden on mobile (mobile header has its own) */}
      <div className="px-4 py-4 border-b border-gray-800 hidden md:block">
        <div className="flex items-center gap-2">
          <Globe className="w-6 h-6 text-blue-400" />
          <span className="text-lg font-semibold tracking-tight">Atlas</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
        {navItems.map((item, i) => {
          if ('type' in item && item.type === 'divider') {
            return <div key={i} className="my-2 border-t border-gray-800" />
          }
          if (!('to' in item)) return null
          const Icon = item.icon
          const spoke = 'spoke' in item ? item.spoke : undefined
          const status = spoke ? spokeMap[spoke] : undefined

          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="flex-1">{item.label}</span>
              {status && (
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    status.online ? 'bg-green-400' : 'bg-red-400'
                  }`}
                  title={status.online ? `Online (${status.latency_ms}ms)` : 'Offline'}
                />
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Status footer */}
      <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-500">
        {spokes.filter(s => s.online).length}/{spokes.length} spokes online
      </div>
    </aside>
  )
}
