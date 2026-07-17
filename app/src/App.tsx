import { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { BookProvider } from './book/BookContext'
import Cover from './pages/Cover'
import Contents from './pages/Contents'
import PageSpread from './pages/PageSpread'
import SearchOverlay from './components/SearchOverlay'

export default function App() {
  const [searchOpen, setSearchOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  // Global shortcuts: "/" or Ctrl/Cmd+K opens search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      const typing = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA'
      if ((e.key === '/' && !typing) || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k')) {
        e.preventDefault()
        setSearchOpen(true)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // Close search on route change
  useEffect(() => setSearchOpen(false), [location.pathname])

  return (
    <BookProvider>
      <div className="desk">
        <Routes>
          <Route path="/" element={<Cover />} />
          <Route path="/contents" element={<Contents onSearch={() => setSearchOpen(true)} />} />
          <Route path="/page/:id" element={<PageSpread onSearch={() => setSearchOpen(true)} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

        {searchOpen && (
          <SearchOverlay
            onClose={() => setSearchOpen(false)}
            onPick={(id) => {
              setSearchOpen(false)
              navigate(`/page/${id}`)
            }}
          />
        )}
      </div>
    </BookProvider>
  )
}
