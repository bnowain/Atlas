import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import DashboardPage from './pages/DashboardPage'
import ChatPage from './pages/ChatPage'
import SearchPage from './pages/SearchPage'
import PeoplePage from './pages/PeoplePage'
import MeetingsPage from './pages/MeetingsPage'
import ArticlesPage from './pages/ArticlesPage'
import MediaBrowserPage from './pages/MediaBrowserPage'
import MessagesPage from './pages/MessagesPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:conversationId" element={<ChatPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/people" element={<PeoplePage />} />
        <Route path="/meetings" element={<MeetingsPage />} />
        <Route path="/articles" element={<ArticlesPage />} />
        <Route path="/files" element={<MediaBrowserPage />} />
        <Route path="/messages" element={<MessagesPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}
