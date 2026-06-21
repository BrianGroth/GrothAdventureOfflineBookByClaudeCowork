import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import TagChip from '../components/TagChip'
import PhotoLightbox from '../components/PhotoLightbox'

interface MediaItem {
  id: number
  sha256: string
  ext: string
  url: string
  width?: number
  height?: number
  alt_text?: string
  caption?: string
  role: string
  position: number
}

interface Tag {
  slug: string
  label: string
  category: string
  color?: string | null
}

interface AdjacentEntry {
  id: number
  title: string
  event_date?: string | null
}

interface EntryData {
  id: number
  title: string
  event_date?: string | null
  publish_date?: string | null
  author?: string | null
  summary?: string
  html_content: string
  permalink: string
  hero?: { url: string; sha256: string; ext: string; width?: number; height?: number; alt_text?: string } | null
  tags: Tag[]
  media: MediaItem[]
  review_flag: boolean
  review_note?: string | null
  prev?: AdjacentEntry | null
  next?: AdjacentEntry | null
}

export default function Entry() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [entry, setEntry] = useState<EntryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const [pageFlip, setPageFlip] = useState<'left' | 'right' | null>(null)
  const articleRef = useRef<HTMLElement>(null)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/entries/${id}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data) => {
        setEntry(data)
        setPageFlip(null)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  // Keyboard prev/next
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' && entry?.prev) navigateTo(entry.prev.id, 'right')
      if (e.key === 'ArrowRight' && entry?.next) navigateTo(entry.next.id, 'left')
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [entry])

  function navigateTo(targetId: number, flipDirection: 'left' | 'right') {
    setPageFlip(flipDirection)
    setTimeout(() => navigate(`/entry/${targetId}`), 320)
  }

  if (loading) {
    return (
      <div className="loading-center" style={{ minHeight: '60vh' }}>
        <div className="spinner" />
        <span>Loading entry…</span>
      </div>
    )
  }

  if (error || !entry) {
    return (
      <div className="empty-state" style={{ paddingTop: '4rem' }}>
        <h2>Entry not found</h2>
        <p>{error || 'This entry does not exist.'}</p>
        <Link to="/" className="btn btn-outline" style={{ marginTop: 'var(--space-4)' }}>
          ← Back to Home
        </Link>
      </div>
    )
  }

  const formattedDate = entry.event_date
    ? new Date(entry.event_date + 'T12:00:00').toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : null

  // All media shown in gallery — no separate hero section on the entry page.
  const galleryPhotos = entry.media.map((m) => ({
    url: m.url,
    alt: m.alt_text,
    caption: m.caption,
    width: m.width,
    height: m.height,
  }))

  const allPhotos = galleryPhotos

  // Strip all <img> and <figure> elements from prose — photos are shown exclusively
  // in the gallery grid below, so they don't also appear inline in the body text.
  function stripImagesFromHtml(html: string): string {
    return html
      .replace(/<figure\b[^>]*>[\s\S]*?<\/figure>/gi, '')
      .replace(/<img\b[^>]*\/?>/gi, '')
      // Clean up empty <a> tags that only wrapped images
      .replace(/<a\b[^>]*>\s*<\/a>/gi, '')
      // Collapse multiple blank lines left by removed blocks
      .replace(/(\s*<p>\s*<\/p>\s*){2,}/gi, '')
  }

  const processedHtml = entry.html_content
    ? stripImagesFromHtml(entry.html_content)
    : ''

  return (
    <>
      {/* Lightbox */}
      {lightboxIndex !== null && (
        <PhotoLightbox
          photos={allPhotos}
          currentIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onPrev={() => setLightboxIndex((i) => (i! > 0 ? i! - 1 : allPhotos.length - 1))}
          onNext={() => setLightboxIndex((i) => (i! < allPhotos.length - 1 ? i! + 1 : 0))}
        />
      )}

      <article
        ref={articleRef}
        className={`entry-page${pageFlip ? ` page-flip-${pageFlip}` : ''}`}
        style={{ maxWidth: 'var(--max-width-prose)', margin: '0 auto', padding: 'var(--space-8) var(--space-6) var(--space-16)' }}
      >
        {/* Back nav */}
        <nav style={{ marginBottom: 'var(--space-8)' }}>
          <button
            onClick={() => navigate(-1)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontFamily: 'var(--font-ui)',
              fontSize: 'var(--text-sm)',
              color: 'var(--color-text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-1)',
              padding: 0,
            }}
          >
            ← Back
          </button>
        </nav>

        {/* Date */}
        {formattedDate && (
          <p
            style={{
              fontFamily: 'var(--font-ui)',
              fontSize: 'var(--text-sm)',
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--color-accent-red)',
              marginBottom: 'var(--space-3)',
            }}
          >
            {formattedDate}
          </p>
        )}

        {/* Title */}
        <h1
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'clamp(1.75rem, 4vw, 2.75rem)',
            fontWeight: 700,
            color: 'var(--color-heading)',
            lineHeight: 'var(--leading-tight)',
            marginBottom: 'var(--space-4)',
          }}
        >
          {entry.title}
        </h1>

        {/* Meta */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-4)',
            marginBottom: 'var(--space-6)',
            paddingBottom: 'var(--space-6)',
            borderBottom: '1px solid var(--color-border)',
            flexWrap: 'wrap',
          }}
        >
          {entry.author && (
            <span style={{ fontFamily: 'var(--font-ui)', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
              By {entry.author}
            </span>
          )}
          {entry.permalink && (
            <a
              href={entry.permalink}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontFamily: 'var(--font-ui)',
                fontSize: 'var(--text-xs)',
                color: 'var(--color-text-muted)',
                textDecoration: 'underline',
                textUnderlineOffset: '2px',
              }}
            >
              Original post ↗
            </a>
          )}
        </div>

        {/* Tags */}
        {entry.tags.length > 0 && (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 'var(--space-2)',
              marginBottom: 'var(--space-8)',
            }}
          >
            {entry.tags.map((t) => (
              <TagChip key={t.slug} {...t} size="md" />
            ))}
          </div>
        )}

        {/* HTML content */}
        {processedHtml ? (
          <div
            className="entry-prose"
            dangerouslySetInnerHTML={{ __html: processedHtml }}
          />
        ) : entry.summary ? (
          <p className="entry-prose">{entry.summary}</p>
        ) : null}

        {/* Photo gallery */}
        {galleryPhotos.length > 0 && (
          <div style={{ marginTop: 'var(--space-10)' }}>
            <h2
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'var(--text-2xl)',
                marginBottom: 'var(--space-6)',
                paddingTop: 'var(--space-6)',
                borderTop: '1px solid var(--color-border)',
              }}
            >
              Photos ({galleryPhotos.length})
            </h2>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                gap: 'var(--space-3)',
              }}
            >
              {galleryPhotos.map((photo, i) => (
                <div
                  key={i}
                  onClick={() => setLightboxIndex(i)}
                  style={{
                    cursor: 'zoom-in',
                    borderRadius: 'var(--radius-sm)',
                    overflow: 'hidden',
                    aspectRatio: '1',
                    background: 'var(--color-parchment)',
                    transition: 'transform var(--transition-fast)',
                  }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.transform = 'scale(1.02)')}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.transform = '')}
                >
                  <img
                    src={photo.url}
                    alt={photo.alt || ''}
                    loading="lazy"
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                </div>
              ))}
            </div>
          </div>
        )}
        {/* Prev / Next page navigation */}
        <nav className="entry-page-nav" aria-label="Entry navigation">
          <div className="entry-page-nav-prev">
            {entry.prev ? (
              <button
                className="page-turn-btn page-turn-prev"
                onClick={() => navigateTo(entry.prev!.id, 'right')}
                title={entry.prev.title}
              >
                <span className="page-turn-arrow">‹</span>
                <span className="page-turn-label">
                  <span className="page-turn-hint">Previous</span>
                  <span className="page-turn-title">{entry.prev.title}</span>
                </span>
              </button>
            ) : (
              <span className="page-turn-placeholder" />
            )}
          </div>
          <div className="entry-page-nav-next">
            {entry.next ? (
              <button
                className="page-turn-btn page-turn-next"
                onClick={() => navigateTo(entry.next!.id, 'left')}
                title={entry.next.title}
              >
                <span className="page-turn-label">
                  <span className="page-turn-hint">Next</span>
                  <span className="page-turn-title">{entry.next.title}</span>
                </span>
                <span className="page-turn-arrow">›</span>
              </button>
            ) : (
              <span className="page-turn-placeholder" />
            )}
          </div>
        </nav>
      </article>
    </>
  )
}
