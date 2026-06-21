import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import PolaroidThumb from './PolaroidThumb'

interface Entry {
  id: number
  title: string
  event_date?: string | null
  summary?: string
  hero?: { url: string; sha256: string; ext: string; alt_text?: string } | null
}

interface YearDrawerProps {
  year: string
  count: number
  defaultOpen?: boolean
}

export default function YearDrawer({ year, count, defaultOpen = false }: YearDrawerProps) {
  const [open, setOpen] = useState(defaultOpen)
  const [entries, setEntries] = useState<Entry[]>([])
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (open && !loaded) {
      setLoading(true)
      fetch(`/api/entries?year=${year}&limit=12&order=asc`)
        .then((r) => r.json())
        .then((data) => {
          setEntries(data.items || [])
          setLoaded(true)
        })
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [open, loaded, year])

  const rotations = [-2, 1.5, -1, 2, -1.5, 1, -2.5, 1.5, -1, 2, -1.5, 1]

  return (
    <div
      style={{
        borderBottom: '1px solid var(--color-border)',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-4)',
          padding: 'var(--space-5) var(--space-6)',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
          transition: 'background var(--transition-fast)',
        }}
        onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = 'var(--color-parchment)')}
        onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = 'none')}
      >
        {/* Chevron */}
        <span
          style={{
            display: 'inline-block',
            fontSize: '0.7rem',
            color: 'var(--color-brown-light)',
            transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform var(--transition-base)',
            flexShrink: 0,
          }}
        >
          ▶
        </span>

        {/* Year */}
        <span
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'var(--text-4xl)',
            fontWeight: 700,
            color: 'var(--color-heading)',
            lineHeight: 1,
          }}
        >
          {year}
        </span>

        {/* Count badge */}
        <span
          style={{
            fontFamily: 'var(--font-ui)',
            fontSize: 'var(--text-sm)',
            color: 'var(--color-text-muted)',
            marginLeft: 'auto',
          }}
        >
          {count} {count === 1 ? 'adventure' : 'adventures'}
        </span>

        {/* See all link */}
        <Link
          to={`/timeline?year=${year}`}
          onClick={(e) => e.stopPropagation()}
          style={{
            fontFamily: 'var(--font-ui)',
            fontSize: 'var(--text-sm)',
            color: 'var(--color-accent-red)',
            fontWeight: 500,
            flexShrink: 0,
          }}
        >
          See all →
        </Link>
      </button>

      {/* Content */}
      {open && (
        <div
          style={{
            padding: 'var(--space-6) var(--space-8) var(--space-8)',
          }}
        >
          {loading ? (
            <div className="loading-center" style={{ padding: 'var(--space-8)' }}>
              <div className="spinner" />
              <span>Loading {year} adventures…</span>
            </div>
          ) : entries.length === 0 ? (
            <p style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-ui)', fontSize: 'var(--text-sm)' }}>
              No entries found for {year}.
            </p>
          ) : (
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 'var(--space-6)',
                alignItems: 'flex-start',
              }}
            >
              {entries.map((entry, i) => (
                <PolaroidThumb
                  key={entry.id}
                  entryId={entry.id}
                  title={entry.title}
                  date={entry.event_date}
                  imageUrl={entry.hero?.url || null}
                  alt={entry.hero?.alt_text || entry.title}
                  rotation={rotations[i % rotations.length]}
                />
              ))}
              {count > 12 && (
                <Link
                  to={`/timeline?year=${year}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '180px',
                    height: '180px',
                    border: '2px dashed var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    fontFamily: 'var(--font-ui)',
                    fontSize: 'var(--text-sm)',
                    color: 'var(--color-text-muted)',
                    textDecoration: 'none',
                    flexDirection: 'column',
                    gap: 'var(--space-2)',
                  }}
                >
                  <span style={{ fontSize: '1.5rem' }}>+{count - 12}</span>
                  <span>more adventures</span>
                </Link>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
