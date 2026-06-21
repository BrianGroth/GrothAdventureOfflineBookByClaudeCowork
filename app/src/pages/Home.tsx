import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import YearDrawer from '../components/YearDrawer'

interface YearSummary {
  year: string
  count: number
}

interface Stats {
  entry_count: number
  media_count: number
  earliest_date: string | null
  latest_date: string | null
  last_sync: string | null
}

export default function Home() {
  const [years, setYears] = useState<YearSummary[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/entries/by-year').then((r) => r.json()),
      fetch('/api/stats').then((r) => r.json()),
    ])
      .then(([yearData, statsData]) => {
        setYears(yearData)
        setStats(statsData)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="loading-center" style={{ minHeight: '60vh' }}>
        <div className="spinner" />
        <span>Loading your scrapbook…</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="empty-state" style={{ paddingTop: '4rem' }}>
        <h2>Could not connect to scrapbook</h2>
        <p>
          Make sure the server is running:<br />
          <code style={{ background: 'var(--color-parchment)', padding: '2px 8px', borderRadius: '3px', fontSize: '0.85em' }}>
            scrapbook serve
          </code>
        </p>
        <p style={{ marginTop: '1rem', color: 'var(--color-text-muted)' }}>{error}</p>
      </div>
    )
  }

  if (years.length === 0) {
    return (
      <div className="empty-state" style={{ paddingTop: '4rem' }}>
        <h2>Your scrapbook is empty</h2>
        <p>
          Run a sync to pull in your adventures:<br />
          <code style={{ background: 'var(--color-parchment)', padding: '2px 8px', borderRadius: '3px', fontSize: '0.85em' }}>
            scrapbook sync --source grothadventures
          </code>
        </p>
      </div>
    )
  }

  const mostRecentYear = years[0]?.year

  return (
    <div>
      {/* Hero banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, var(--color-brown-dark) 0%, var(--color-brown) 60%, var(--color-brown-light) 100%)',
          color: 'var(--color-cream)',
          padding: 'var(--space-16) var(--space-6) var(--space-12)',
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Decorative texture */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Ccircle cx=\'30\' cy=\'30\' r=\'1\' fill=\'rgba(255,255,255,0.04)\'/%3E%3C/svg%3E") repeat',
            pointerEvents: 'none',
          }}
        />

        <h1
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'clamp(2rem, 6vw, 4rem)',
            fontWeight: 800,
            marginBottom: 'var(--space-4)',
            textShadow: '0 2px 8px rgba(0,0,0,0.3)',
          }}
        >
          Groth Adventures
        </h1>
        <p
          style={{
            fontFamily: 'var(--font-body)',
            fontStyle: 'italic',
            fontSize: 'var(--text-xl)',
            opacity: 0.85,
            marginBottom: 'var(--space-8)',
          }}
        >
          A family scrapbook of adventures, memories, and moments
        </p>

        {/* Stats row */}
        {stats && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              gap: 'var(--space-8)',
              flexWrap: 'wrap',
            }}
          >
            {[
              { label: 'Adventures', value: stats.entry_count.toLocaleString() },
              { label: 'Photos', value: stats.media_count.toLocaleString() },
              { label: 'Years', value: years.length.toString() },
            ].map(({ label, value }) => (
              <div key={label} style={{ textAlign: 'center' }}>
                <div
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: 'var(--text-3xl)',
                    fontWeight: 700,
                    lineHeight: 1,
                  }}
                >
                  {value}
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-ui)',
                    fontSize: 'var(--text-xs)',
                    opacity: 0.7,
                    letterSpacing: '0.1em',
                    textTransform: 'uppercase',
                    marginTop: 'var(--space-1)',
                  }}
                >
                  {label}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* CTA buttons */}
        <div
          style={{
            marginTop: 'var(--space-8)',
            display: 'flex',
            gap: 'var(--space-3)',
            justifyContent: 'center',
          }}
        >
          <Link
            to="/timeline"
            style={{
              fontFamily: 'var(--font-ui)',
              fontWeight: 600,
              padding: 'var(--space-3) var(--space-6)',
              background: 'rgba(255,255,255,0.15)',
              color: 'var(--color-cream)',
              border: '1px solid rgba(255,255,255,0.3)',
              borderRadius: 'var(--radius-md)',
              textDecoration: 'none',
              fontSize: 'var(--text-sm)',
              transition: 'background var(--transition-fast)',
            }}
            onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.25)')}
            onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.15)')}
          >
            Browse Timeline
          </Link>
          {mostRecentYear && (
            <Link
              to={`/search?q=`}
              style={{
                fontFamily: 'var(--font-ui)',
                fontWeight: 600,
                padding: 'var(--space-3) var(--space-6)',
                background: 'var(--color-cream)',
                color: 'var(--color-brown-dark)',
                border: '1px solid transparent',
                borderRadius: 'var(--radius-md)',
                textDecoration: 'none',
                fontSize: 'var(--text-sm)',
                transition: 'background var(--transition-fast)',
              }}
            >
              Search Adventures
            </Link>
          )}
        </div>
      </div>

      {/* Year drawers */}
      <div style={{ maxWidth: 'var(--max-width)', margin: '0 auto' }}>
        <div
          style={{
            padding: 'var(--space-8) var(--space-6) var(--space-4)',
            fontFamily: 'var(--font-display)',
            fontSize: 'var(--text-2xl)',
            color: 'var(--color-heading)',
            borderBottom: '2px solid var(--color-border)',
          }}
        >
          Adventures by Year
        </div>

        {years.map((ys, i) => (
          <YearDrawer
            key={ys.year}
            year={ys.year}
            count={ys.count}
            defaultOpen={i === 0}
          />
        ))}

        {stats?.last_sync && (
          <p
            style={{
              padding: 'var(--space-6)',
              fontFamily: 'var(--font-ui)',
              fontSize: 'var(--text-xs)',
              color: 'var(--color-text-muted)',
              textAlign: 'right',
            }}
          >
            Last synced: {new Date(stats.last_sync).toLocaleString()}
          </p>
        )}
      </div>
    </div>
  )
}
