import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import TimelineCard from '../components/TimelineCard'

interface Entry {
  id: number
  title: string
  event_date?: string | null
  summary?: string
  hero?: { url: string; sha256: string; ext: string; alt_text?: string } | null
  tags?: Array<{ slug: string; label: string; category: string; color?: string | null }>
}

export default function Timeline() {
  const [searchParams, setSearchParams] = useSearchParams()
  const yearFilter = searchParams.get('year')

  const [entries, setEntries] = useState<Entry[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [nextCursor, setNextCursor] = useState<number | null>(null)
  const [hasMore, setHasMore] = useState(false)

  const sentinelRef = useRef<HTMLDivElement>(null)

  const fetchEntries = useCallback(
    async (cursor?: number, replace = false) => {
      const params = new URLSearchParams({ limit: '24' })
      if (yearFilter) params.set('year', yearFilter)
      if (cursor) params.set('cursor', String(cursor))

      const r = await fetch(`/api/entries?${params}`)
      const data = await r.json()

      if (replace) {
        setEntries(data.items)
      } else {
        setEntries((prev) => [...prev, ...data.items])
      }
      setNextCursor(data.next_cursor)
      setHasMore(data.has_more)
    },
    [yearFilter],
  )

  useEffect(() => {
    setLoading(true)
    setEntries([])
    setNextCursor(null)
    fetchEntries(undefined, true).finally(() => setLoading(false))
  }, [fetchEntries])

  // Infinite scroll
  useEffect(() => {
    if (!sentinelRef.current || !hasMore) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore) {
          setLoadingMore(true)
          fetchEntries(nextCursor ?? undefined).finally(() => setLoadingMore(false))
        }
      },
      { rootMargin: '200px' },
    )
    observer.observe(sentinelRef.current)
    return () => observer.disconnect()
  }, [sentinelRef, hasMore, loadingMore, nextCursor, fetchEntries])

  if (loading) {
    return (
      <div className="loading-center" style={{ minHeight: '60vh' }}>
        <div className="spinner" />
        <span>Loading timeline…</span>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 'var(--max-width)', margin: '0 auto', padding: 'var(--space-8) var(--space-6)' }}>
      {/* Header */}
      <div style={{ marginBottom: 'var(--space-10)' }}>
        <h1
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'var(--text-4xl)',
            color: 'var(--color-heading)',
            marginBottom: 'var(--space-2)',
          }}
        >
          {yearFilter ? `${yearFilter} Adventures` : 'All Adventures'}
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-ui)', fontSize: 'var(--text-sm)' }}>
          {entries.length} {entries.length === 1 ? 'entry' : 'entries'} loaded
          {yearFilter && (
            <> · <Link to="/timeline" style={{ color: 'var(--color-accent-red)' }}>Clear filter</Link></>
          )}
        </p>
      </div>

      {entries.length === 0 ? (
        <div className="empty-state">
          <h2>No adventures found</h2>
          <p>Try syncing the blog first: <code>scrapbook sync --source grothadventures</code></p>
        </div>
      ) : (
        <>
          {/* Timeline layout */}
          <div style={{ position: 'relative' }}>
            {/* Center spine */}
            <div
              style={{
                position: 'absolute',
                left: '50%',
                top: 0,
                bottom: 0,
                width: '2px',
                background: 'linear-gradient(to bottom, var(--color-tan), var(--color-brown-light) 20%, var(--color-brown-light) 80%, var(--color-tan))',
                transform: 'translateX(-50%)',
              }}
            />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
              {entries.map((entry, i) => {
                const side = i % 2 === 0 ? 'left' : 'right'
                return (
                  <div
                    key={entry.id}
                    style={{ position: 'relative', display: 'grid', gridTemplateColumns: '1fr 40px 1fr' }}
                  >
                    {/* Left slot */}
                    <div style={{ paddingRight: 'var(--space-6)' }}>
                      {side === 'left' && (
                        <TimelineCard {...entry} side="left" />
                      )}
                    </div>

                    {/* Center dot */}
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', paddingTop: 'var(--space-5)' }}>
                      <div
                        style={{
                          width: '14px',
                          height: '14px',
                          borderRadius: '50%',
                          background: 'var(--color-accent-red)',
                          border: '2px solid var(--color-cream)',
                          boxShadow: '0 0 0 2px var(--color-brown-light)',
                          flexShrink: 0,
                        }}
                      />
                    </div>

                    {/* Right slot */}
                    <div style={{ paddingLeft: 'var(--space-6)' }}>
                      {side === 'right' && (
                        <TimelineCard {...entry} side="right" />
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Infinite scroll sentinel */}
          <div ref={sentinelRef} style={{ height: '60px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {loadingMore && (
              <div className="loading-center" style={{ padding: 'var(--space-4)' }}>
                <div className="spinner" style={{ width: '24px', height: '24px' }} />
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
