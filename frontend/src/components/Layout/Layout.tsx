import { useState, type ReactNode } from 'react'
import { Menu, Globe } from 'lucide-react'
import Sidebar from './Sidebar'

export default function Layout({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex flex-col md:flex-row h-screen overflow-hidden">
      {/* Mobile header bar */}
      <div className="md:hidden flex items-center h-12 px-3 border-b border-gray-800 bg-gray-900 shrink-0 gap-2">
        <button
          onClick={() => setSidebarOpen(true)}
          className="p-1.5 rounded-lg hover:bg-gray-800 transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
        <Globe className="w-5 h-5 text-blue-400" />
        <span className="text-sm font-semibold tracking-tight">Atlas</span>
      </div>

      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar: overlay on mobile, static on desktop */}
      <div
        className={`
          fixed inset-y-0 left-0 z-40 w-56 transform transition-transform duration-200
          md:static md:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <Sidebar onNavigate={() => setSidebarOpen(false)} />
      </div>

      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
