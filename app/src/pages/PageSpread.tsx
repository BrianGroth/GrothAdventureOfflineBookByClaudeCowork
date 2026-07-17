import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  useBook,
  saveBookmark,
  formatDate,
  prefersReducedMotion,
  EntryDetail,
} from '../book/BookContext'
import PhotoLightbox from '../components/PhotoLightbox'

interface PageSpreadProps {
  onSearch: () => void
}

const FLIP_MS = 560
const FLIP_SWAP_MS = 250

/** Photos live on the verso page; drop them (and stray iframes) from the prose. */
function stripMediaFromHtml(html: string): string {
  return html
    .replace(/<figure\b[^>]*>[\s\S]*?<\/figure>/gi, '')
    .replace(/<img\b[^>]*\/?>/gi, '')
    .replace(/<iframe\b[^>]*>[\s\S]*?<\/iframe>/gi, '')
    .replace(/<a\b[^>]*>\s*<\/a>/gi, '')
    .replace(/(\s*<p>\s*<\/p>\s*){1,}/gi, '')
}

const TILT = [-2.2, 1.6, -1.2, 2.1, -1.7, 0.9, -0.6, 1.3]

export default function PageSpread({ onSearch }: PageSpreadProps) {
  const { id } = useParams<{ id: string }>()
  const entryId = Number(id)
  const navigate = useNavigate()
  const { loading, error, navFor, getEntry, prefetchEntry, entries } = useBook()

  const [detail, setDetail] = useState<EntryDetail | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const [flip, setFlip] = useState<'next' | 'prev' | null>(null)
  const flipping = useRef(false)

  const nav = navFor(entryId)
  const contentsUrl = nav ? `/contents?view=chapters&chapter=${nav.entry.topic}` : '/contents'

  // Load entry content
  useEffect(() => {
    if (!entries.length) return
    let alive = true
    setDetailError(null)
    getEntry(entryId)
      .then((d) => alive && setDetail(d))
      .catch((e) => alive && setDetailError(e.message))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entryId, entries.length])

  // Bookmark + prefetch neighbours
  useEffect(() => {
    if (!nav) return
    saveBookmark(nav.entry.id, nav.entry.title)
    if (nav.nextDate) prefetchEntry(nav.nextDate.id)
    if (nav.prevDate) prefetchEntry(nav.prevDate.id)
    if (nav.nextTopic) prefetchEntry(nav.nextTopic.id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entryId, entries.length])

  function turnTo(targetId: number | undefined, dir: 'next' | 'prev') {
    if (targetId == null || flipping.current) return
    if (prefersReducedMotion()) {
      navigate(`/page/${targetId}`)
      return
    }
    flipping.current = true
    setFlip(dir)
    // Swap the content beneath the turning sheet, then lift the sheet away.
    window.setTimeout(() => navigate(`/page/${targetId}`), FLIP_SWAP_MS)
    window.setTimeout(() => {
      setFlip(null)
      flipping.current = false
    }, FLIP_MS)
  }

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (lightboxIndex !== null) return // lightbox handles its own keys
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return
      switch (e.key) {
        case 'ArrowRight':
          turnTo(nav?.nextDate?.id, 'next')
          break
        case 'ArrowLeft':
          turnTo(nav?.prevDate?.id, 'prev')
          break
        case ']':
          turnTo(nav?.nextTopic?.id, 'next')
          break
        case '[':
          turnTo(nav?.prevTopic?.id, 'prev')
          break
        case 'c':
        case 'C':
        case 'Escape':
          navigate(contentsUrl)
          break
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nav, lightboxIndex])

  if (loading) {
    return <div className="desk-message"><span className="desk-spinner" /> Opening the book…</div>
  }
  if (error || !nav) {
    return (
      <div className="desk-message">
        <h2>{error ? 'The book could not be opened' : 'This page is missing'}</h2>
        {error && <p className="desk-message-detail">{error}</p>}
        <Link to="/contents" className="cover-btn">Back to Contents</Link>
      </div>
    )
  }

  const { entry, pageNo, total, prevDate, nextDate, topic, topicIndex, topicCount, prevTopic, nextTopic } = nav
  const isStale = detail !== null && detail.id !== entry.id

  const photos = (!isStale && detail?.media) ? detail.media : []
  const lead = photos[0] || null
  const restRaw = photos.slice(1)
  const maxThumbs = 6
  const thumbs = restRaw.slice(0, maxThumbs)
  const overflow = restRaw.length - thumbs.length

  const lightboxPhotos = photos.map((m) => ({
    url: m.url,
    alt: m.alt_text,
    caption: m.caption,
    width: m.width,
    height: m.height,
  }))

  const prose = !isStale && detail?.html_content ? stripMediaFromHtml(detail.html_content) : ''
  const chapterColor = topic?.color || 'var(--brown)'

  return (
    <div className="book-scene">
      {lightboxIndex !== null && (
        <PhotoLightbox
          photos={lightboxPhotos}
          currentIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onPrev={() => setLightboxIndex((i) => (i! > 0 ? i! - 1 : lightboxPhotos.length - 1))}
          onNext={() => setLightboxIndex((i) => (i! < lightboxPhotos.length - 1 ? i! + 1 : 0))}
        />
      )}

      <div className="book-toolbar">
        <Link to={contentsUrl} className="toolbar-btn" title="Table of contents (C)">
          ☰ Contents
        </Link>
        <span className="toolbar-title">Groth Adventures</span>
        <button className="toolbar-btn" onClick={onSearch} title="Search (press /)">
          ⌕ Search
        </button>
      </div>

      <div className="book page-book">
        <div className="ribbon" title="Your place is saved" aria-hidden="true" />

        <div className="spread">
          {/* ── Verso: photographs ── */}
          <div className="page verso">
            <div className="running-head">
              <span>Groth Adventures</span>
            </div>
            <div className="page-inner photo-page">
              {detailError && (
                <p className="page-error">Could not load this story ({detailError}).</p>
              )}
              {!detailError && !lead && detail && !isStale && (
                <div className="no-photos">
                  <span className="no-photos-stamp">NO PHOTOGRAPHS</span>
                  <p>{entry.snippet}</p>
                </div>
              )}
              {lead && (
                <figure
                  className="polaroid lead"
                  style={{ ['--tilt' as string]: `${TILT[entry.id % TILT.length] * 0.6}deg` }}
                  onClick={() => setLightboxIndex(0)}
                >
                  <span className="tape" aria-hidden="true" />
                  <img src={lead.url} alt={lead.alt_text || entry.title} />
                  {lead.caption && <figcaption>{lead.caption}</figcaption>}
                </figure>
              )}
              {thumbs.length > 0 && (
                <div className="photo-thumbs">
                  {thumbs.map((m, i) => (
                    <button
                      key={m.id}
                      className="polaroid thumb"
                      style={{ ['--tilt' as string]: `${TILT[(entry.id + i + 1) % TILT.length]}deg` }}
                      onClick={() => setLightboxIndex(i + 1)}
                      aria-label={`Photo ${i + 2} of ${photos.length}`}
                    >
                      <img src={m.url} alt={m.alt_text || ''} loading="lazy" />
                      {overflow > 0 && i === thumbs.length - 1 && (
                        <span className="thumb-more">+{overflow}</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
              {photos.length > 1 && (
                <p className="photo-count-note">
                  {photos.length} photographs — click any to view
                </p>
              )}
            </div>
            <div className="folio folio-left">
              Page {pageNo} · {entry.event_date?.slice(0, 4)}
            </div>
          </div>

          <div className="spine" aria-hidden="true" />

          {/* ── Recto: the story ── */}
          <div className="page recto">
            <div className="running-head">
              <span style={{ color: chapterColor }}>{topic?.label}</span>
            </div>
            <div className="page-inner story-page">
              <Link
                to={contentsUrl}
                className="chapter-eyebrow linked"
                style={{ color: chapterColor }}
                title="View this chapter in the contents"
              >
                {topic?.emoji} {topic?.label} · {topicIndex} of {topicCount}
              </Link>
              <p className="story-date">{formatDate(entry.event_date)}</p>
              <h1 className="story-title">{entry.title}</h1>

              {prose ? (
                <div className="story-prose" dangerouslySetInnerHTML={{ __html: prose }} />
              ) : detail && !isStale ? (
                <p className="story-prose muted">
                  {entry.snippet || 'A story told in photographs.'}
                </p>
              ) : (
                <p className="story-prose muted">…</p>
              )}

              {entry.keywords.length > 0 && (
                <div className="story-tags">
                  {entry.keywords.map((k) => (
                    <span key={k} className="story-tag">{k}</span>
                  ))}
                </div>
              )}

              {detail && !isStale && detail.permalink && (
                <a
                  className="story-permalink"
                  href={detail.permalink}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Original post ↗
                </a>
              )}
            </div>
            <div className="folio folio-right">
              {pageNo} of {total}
            </div>
          </div>

          {/* ── Turning sheet overlay ── */}
          {flip && (
            <div className={`flip-sheet flip-${flip}`} aria-hidden="true">
              <div className="flip-face front" />
              <div className="flip-face back" />
            </div>
          )}
          {flip && <div className={`flip-shade flip-${flip}`} aria-hidden="true" />}
        </div>

        {/* ── Edge page-turn zones ── */}
        <button
          className="edge-nav prev"
          onClick={() => turnTo(prevDate?.id, 'prev')}
          disabled={!prevDate}
          title={prevDate ? `Previous: ${prevDate.title}  (←)` : 'This is the first page'}
          aria-label={prevDate ? `Previous page: ${prevDate.title}` : 'No previous page'}
        >
          <span className="edge-arrow">‹</span>
          {prevDate && (
            <span className="edge-peek">
              <span className="edge-peek-hint">← {formatDate(prevDate.event_date, 'short')}</span>
              <span className="edge-peek-title">{prevDate.title}</span>
            </span>
          )}
        </button>
        <button
          className="edge-nav next"
          onClick={() => turnTo(nextDate?.id, 'next')}
          disabled={!nextDate}
          title={nextDate ? `Next: ${nextDate.title}  (→)` : 'This is the last page'}
          aria-label={nextDate ? `Next page: ${nextDate.title}` : 'No next page'}
        >
          <span className="edge-arrow">›</span>
          {nextDate && (
            <span className="edge-peek">
              <span className="edge-peek-hint">{formatDate(nextDate.event_date, 'short')} →</span>
              <span className="edge-peek-title">{nextDate.title}</span>
            </span>
          )}
        </button>
      </div>

      {/* ── Chapter thread navigation ── */}
      <div className="chapter-nav">
        <button
          className="chapter-nav-btn"
          onClick={() => turnTo(prevTopic?.id, 'prev')}
          disabled={!prevTopic}
          title={prevTopic ? `Earlier in chapter: ${prevTopic.title}  ([)` : 'First story in this chapter'}
        >
          ‹
        </button>
        <Link to={contentsUrl} className="chapter-nav-label" title="View chapter contents">
          <span aria-hidden="true">{topic?.emoji}</span> {topic?.label}
          <span className="chapter-nav-count">{topicIndex} / {topicCount}</span>
        </Link>
        <button
          className="chapter-nav-btn"
          onClick={() => turnTo(nextTopic?.id, 'next')}
          disabled={!nextTopic}
          title={nextTopic ? `Next in chapter: ${nextTopic.title}  (])` : 'Last story in this chapter'}
        >
          ›
        </button>
      </div>
    </div>
  )
}
