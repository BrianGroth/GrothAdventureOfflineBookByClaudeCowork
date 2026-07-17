import { useEffect, useRef, useState } from 'react'
import { useBook, formatDate } from '../book/BookContext'

interface SearchResult {
  id: number
  title: string
  event_date: string | null
  snippet: string
  hero?: { url: string } | null
}

interface SearchOverlayProps {
  onClose: () => void
  onPick: (id: number) => void
}

export default function SearchOverlay({ onClose, onPick }: SearchOverlayProps) {
  const { pageNo } = useBook()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [active, setActive] = useState(0)
  const [searching, setSearching] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const debounce = useRef<number>()

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    window.clearTimeout(debounce.current)
    const q = query.trim()
    if (!q) {
      setResults([])
      return
    }
    debounce.current = window.setTimeout(() => {
      setSearching(true)
      fetch(`/api/search?q=${encodeURIComponent(q)}&limit=12`)
        .then((r) => r.json())
        .then((data) => {
          setResults(data.items || [])
          setActive(0)
        })
        .catch(() => setResults([]))
        .finally(() => setSearching(false))
    }, 220)
    return () => window.clearTimeout(debounce.current)
  }, [query])

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Escape') onClose()
    else if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => Math.min(a + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => Math.max(a - 1, 0))
    } else if (e.key === 'Enter' && results[active]) {
      onPick(results[active].id)
    }
  }

  return (
    <div className="search-scrim" onClick={onClose}>
      <div
        className="search-card"
        role="dialog"
        aria-label="Search the book"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKey}
      >
        <div className="search-input-row">
          <span className="search-glyph" aria-hidden="true">⌕</span>
          <input
            ref={inputRef}
            type="search"
            value={query}
            placeholder="Search the whole book…"
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search"
          />
          <button className="search-close" onClick={onClose} aria-label="Close search">✕</button>
        </div>

        {query.trim() && (
          <div className="search-results">
            {searching && results.length === 0 && (
              <p className="search-note">Searching…</p>
            )}
            {!searching && results.length === 0 && (
              <p className="search-note">Nothing found for “{query.trim()}”.</p>
            )}
            {results.map((r, i) => (
              <button
                key={r.id}
                className={`search-result${i === active ? ' active' : ''}`}
                onMouseEnter={() => setActive(i)}
                onClick={() => onPick(r.id)}
              >
                {r.hero ? (
                  <img className="search-thumb" src={r.hero.url} alt="" loading="lazy" />
                ) : (
                  <span className="search-thumb empty" aria-hidden="true">✈</span>
                )}
                <span className="search-result-text">
                  <span className="search-result-title">{r.title}</span>
                  <span className="search-result-meta">
                    {formatDate(r.event_date, 'short')}
                    {pageNo.get(r.id) ? ` · page ${pageNo.get(r.id)}` : ''}
                  </span>
                  {r.snippet && (
                    <span
                      className="search-result-snippet"
                      dangerouslySetInnerHTML={{ __html: r.snippet }}
                    />
                  )}
                </span>
              </button>
            ))}
          </div>
        )}

        <div className="search-footer">
          <span><kbd>↑</kbd><kbd>↓</kbd> choose</span>
          <span><kbd>Enter</kbd> open page</span>
          <span><kbd>Esc</kbd> close</span>
        </div>
      </div>
    </div>
  )
}
