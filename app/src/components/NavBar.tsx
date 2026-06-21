import { useState, useEffect } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'

export default function NavBar() {
  const [searchQuery, setSearchQuery] = useState('')
  const [scrolled, setScrolled] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', handler, { passive: true })
    return () => window.removeEventListener('scroll', handler)
  }, [])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`)
    }
  }

  return (
    <nav
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 'var(--nav-height)',
        zIndex: 100,
        background: scrolled
          ? 'rgba(253, 248, 240, 0.97)'
          : 'var(--color-cream)',
        borderBottom: '1px solid var(--color-border)',
        boxShadow: scrolled ? 'var(--shadow-sm)' : 'none',
        backdropFilter: scrolled ? 'blur(8px)' : 'none',
        transition: 'all var(--transition-base)',
      }}
    >
      <div
        className="container"
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-6)',
        }}
      >
        {/* Logo / Title */}
        <Link
          to="/"
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'var(--text-xl)',
            fontWeight: 700,
            color: 'var(--color-heading)',
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}
        >
          ✈ Groth Adventures
        </Link>

        {/* Nav links */}
        <div
          style={{
            display: 'flex',
            gap: 'var(--space-4)',
            fontFamily: 'var(--font-ui)',
            fontSize: 'var(--text-sm)',
            fontWeight: 500,
          }}
        >
          <NavLink
            to="/"
            end
            style={({ isActive }) => ({
              color: isActive ? 'var(--color-accent-red)' : 'var(--color-text-muted)',
              padding: 'var(--space-1) var(--space-2)',
              borderRadius: 'var(--radius-sm)',
              transition: 'color var(--transition-fast)',
            })}
          >
            Home
          </NavLink>
          <NavLink
            to="/timeline"
            style={({ isActive }) => ({
              color: isActive ? 'var(--color-accent-red)' : 'var(--color-text-muted)',
              padding: 'var(--space-1) var(--space-2)',
              borderRadius: 'var(--radius-sm)',
              transition: 'color var(--transition-fast)',
            })}
          >
            Timeline
          </NavLink>
        </div>

        {/* Search form */}
        <form
          onSubmit={handleSearch}
          style={{
            marginLeft: 'auto',
            display: 'flex',
            gap: 'var(--space-2)',
          }}
        >
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search adventures…"
            style={{
              fontFamily: 'var(--font-ui)',
              fontSize: 'var(--text-sm)',
              padding: 'var(--space-2) var(--space-3)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-surface)',
              color: 'var(--color-text)',
              width: '200px',
              outline: 'none',
              transition: 'border-color var(--transition-fast)',
            }}
            onFocus={(e) => (e.target.style.borderColor = 'var(--color-brown)')}
            onBlur={(e) => (e.target.style.borderColor = 'var(--color-border)')}
          />
          <button type="submit" className="btn btn-primary" style={{ padding: 'var(--space-2) var(--space-3)' }}>
            Search
          </button>
        </form>
      </div>
    </nav>
  )
}
