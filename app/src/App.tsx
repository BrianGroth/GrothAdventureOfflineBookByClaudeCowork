import { Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import Home from './pages/Home'
import Timeline from './pages/Timeline'
import Entry from './pages/Entry'
import Search from './pages/Search'

export default function App() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <NavBar />
      <main style={{ flex: 1, paddingTop: 'var(--nav-height)' }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/timeline" element={<Timeline />} />
          <Route path="/entry/:id" element={<Entry />} />
          <Route path="/search" element={<Search />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  )
}

function NotFound() {
  return (
    <div className="empty-state" style={{ paddingTop: '6rem' }}>
      <h2>Page Not Found</h2>
      <p>The page you were looking for doesn't exist.</p>
    </div>
  )
}
