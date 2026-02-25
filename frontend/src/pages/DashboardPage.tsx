import { useNavigate } from 'react-router-dom'
import { MessageSquare, Search } from 'lucide-react'
import DashboardGrid from '../components/Dashboard/DashboardGrid'
import { useSpokeStatus } from '../hooks/useSpokeStatus'

export default function DashboardPage() {
  const { spokes, loading } = useSpokeStatus()
  const navigate = useNavigate()

  return (
    <div className="max-w-4xl mx-auto px-3 md:px-6 py-4 md:py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold mb-1">Atlas</h1>
        <p className="text-gray-500 text-sm">Civic accountability orchestration hub</p>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-3 mb-8">
        <button
          onClick={() => navigate('/chat')}
          className="flex items-center gap-3 bg-gray-800 hover:bg-gray-750 border border-gray-700 rounded-xl px-4 py-3 transition-colors text-left"
        >
          <MessageSquare className="w-5 h-5 text-blue-400" />
          <div>
            <div className="text-sm font-medium">New Chat</div>
            <div className="text-xs text-gray-500">Ask a question across all sources</div>
          </div>
        </button>
        <button
          onClick={() => navigate('/search')}
          className="flex items-center gap-3 bg-gray-800 hover:bg-gray-750 border border-gray-700 rounded-xl px-4 py-3 transition-colors text-left"
        >
          <Search className="w-5 h-5 text-emerald-400" />
          <div>
            <div className="text-sm font-medium">Search</div>
            <div className="text-xs text-gray-500">Search across all connected apps</div>
          </div>
        </button>
      </div>

      {/* Spoke status */}
      <div className="mb-4">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">Connected Apps</h2>
      </div>
      {loading ? (
        <div className="text-gray-500 text-sm">Checking spokes...</div>
      ) : (
        <DashboardGrid spokes={spokes} />
      )}
    </div>
  )
}
