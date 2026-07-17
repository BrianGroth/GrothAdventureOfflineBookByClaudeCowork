import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useBook, getBookmark, prefersReducedMotion } from '../book/BookContext'

export default function Cover() {
  const { loading, error, entries } = useBook()
  const navigate = useNavigate()
  const [opening, setOpening] = useState(false)
  const bookmark = getBookmark()

  const years = entries.length
    ? `${entries[0].event_date?.slice(0, 4)} – ${entries[entries.length - 1].event_date?.slice(0, 4)}`
    : ''
  const photoTotal = entries.reduce((n, e) => n + e.photos, 0)

  function open(to: string) {
    if (opening) return
    if (prefersReducedMotion()) {
      navigate(to)
      return
    }
    setOpening(true)
    setTimeout(() => navigate(to), 650)
  }

  if (error) {
    return (
      <div className="desk-message">
        <h2>The book could not be opened</h2>
        <p>Make sure the server is running: <code>scrapbook serve</code></p>
        <p className="desk-message-detail">{error}</p>
      </div>
    )
  }

  return (
    <div className="cover-scene">
      <div
        className={`book-cover${opening ? ' opening' : ''}`}
        onClick={() => open(bookmark ? `/page/${bookmark.id}` : '/contents')}
        role="button"
        aria-label="Open the book"
      >
        <div className="cover-frame">
          <div className="cover-ornament">✦ ✦ ✦</div>
          <h1 className="cover-title">
            Groth<br />Adventures
          </h1>
          <div className="cover-rule" />
          <p className="cover-subtitle">A Family Scrapbook</p>
          {years && <p className="cover-years">{years}</p>}
          <div className="cover-compass" aria-hidden="true">✈</div>
          {!loading && entries.length > 0 && (
            <p className="cover-stats">
              {entries.length} adventures · {photoTotal.toLocaleString()} photographs
            </p>
          )}
        </div>
        <div className="cover-spine-edge" aria-hidden="true" />
      </div>

      <div className="cover-actions">
        {loading ? (
          <span className="cover-hint">Opening the archive…</span>
        ) : (
          <>
            <button className="cover-btn primary" onClick={() => open('/contents')}>
              Open the Book
            </button>
            {bookmark && (
              <button className="cover-btn" onClick={() => open(`/page/${bookmark.id}`)}>
                <span className="ribbon-dot" aria-hidden="true" /> Resume — {bookmark.title}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}
