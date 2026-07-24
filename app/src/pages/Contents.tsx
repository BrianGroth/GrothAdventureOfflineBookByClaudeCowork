import { useEffect, useMemo } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useBook, getBookmark, formatDate, TocEntry } from '../book/BookContext'

interface ContentsProps {
  onSearch: () => void
}

const NUMBER_WORDS = [
  'No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
  'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
  'Seventeen', 'Eighteen', 'Nineteen', 'Twenty',
]

/** Spelled-out count — reads better than a digit in the book's voice. */
function countWord(n: number): string {
  return NUMBER_WORDS[n] ?? String(n)
}

export default function Contents({ onSearch }: ContentsProps) {
  const { loading, error, topics, entries, topicEntries, pageNo } = useBook()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()

  const view = params.get('view') === 'dates' ? 'dates' : 'chapters'
  const bookmark = getBookmark()

  const years = useMemo(() => {
    const map = new Map<string, TocEntry[]>()
    entries.forEach((e) => {
      const y = e.event_date?.slice(0, 4) || '—'
      if (!map.has(y)) map.set(y, [])
      map.get(y)!.push(e)
    })
    return [...map.entries()] // chronological, book order
  }, [entries])

  const visibleTopics = topics.filter((t) => (topicEntries.get(t.slug) || []).length > 0)

  const selChapter = params.get('chapter') || visibleTopics[0]?.slug || ''
  const selYear = params.get('year') || years[0]?.[0] || ''

  // Keyboard: Escape returns to cover
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') navigate('/')
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [navigate])

  const chapterDetail = topicEntries.get(selChapter) || []
  const chapterInfo = visibleTopics.find((t) => t.slug === selChapter)
  const yearDetail = years.find(([y]) => y === selYear)?.[1] || []

  const monthGroups = useMemo(() => {
    const map = new Map<string, TocEntry[]>()
    yearDetail.forEach((e) => {
      const m = formatDate(e.event_date, 'month')
      if (!map.has(m)) map.set(m, [])
      map.get(m)!.push(e)
    })
    return [...map.entries()]
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selYear, years])

  if (loading) {
    return <div className="desk-message"><span className="desk-spinner" /> Opening the book…</div>
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

  function setView(v: 'chapters' | 'dates') {
    const next = new URLSearchParams(params)
    next.set('view', v)
    setParams(next, { replace: true })
  }

  function select(key: 'chapter' | 'year', value: string) {
    const next = new URLSearchParams(params)
    next.set(key, value)
    setParams(next, { replace: true })
  }

  function EntryRow({ e }: { e: TocEntry }) {
    const isBookmarked = bookmark?.id === e.id
    return (
      <Link to={`/page/${e.id}`} className={`toc-row${isBookmarked ? ' bookmarked' : ''}`}>
        {e.cover ? (
          <img className="toc-thumb" src={e.cover.url} alt="" loading="lazy" />
        ) : (
          <span className="toc-thumb empty" aria-hidden="true">✈</span>
        )}
        <span className="toc-row-text">
          <span className="toc-row-title">
            {e.title}
            {isBookmarked && <span className="toc-ribbon-mark" title="Your bookmark">🔖</span>}
          </span>
          <span className="toc-row-date">{formatDate(e.event_date, 'short')}</span>
        </span>
        <span className="toc-leader" aria-hidden="true" />
        <span className="toc-pageno">{pageNo.get(e.id)}</span>
      </Link>
    )
  }

  return (
    <div className="book-scene">
      <div className="book-toolbar">
        <Link to="/" className="toolbar-btn" title="Back to cover">‹ Cover</Link>
        <span className="toolbar-title">Groth Adventures</span>
        <button className="toolbar-btn" onClick={onSearch} title="Search (press /)">
          ⌕ Search
        </button>
      </div>

      <div className="book contents-book">
        {/* Index tabs poking out of the top edge */}
        <div className="book-tabs" role="tablist" aria-label="Table of contents view">
          <button
            role="tab"
            aria-selected={view === 'chapters'}
            className={`book-tab${view === 'chapters' ? ' active' : ''}`}
            onClick={() => setView('chapters')}
          >
            By Chapter
          </button>
          <button
            role="tab"
            aria-selected={view === 'dates'}
            className={`book-tab${view === 'dates' ? ' active' : ''}`}
            onClick={() => setView('dates')}
          >
            By Date
          </button>
        </div>

        <div className="spread">
          <div className="page verso">
            <div className="page-inner">
              <header className="toc-header">
                <h2 className="toc-heading">Contents</h2>
                <p className="toc-subheading">
                  {view === 'chapters'
                    ? `${countWord(visibleTopics.length)} chapters of family adventures`
                    : 'Every page, in the order it happened'}
                </p>
              </header>

              {view === 'chapters' ? (
                <nav className="chapter-list" aria-label="Chapters">
                  {visibleTopics.map((t, i) => (
                    <button
                      key={t.slug}
                      className={`chapter-item${t.slug === selChapter ? ' selected' : ''}`}
                      style={{ ['--chapter-color' as string]: t.color || 'var(--brown)' }}
                      onClick={() => select('chapter', t.slug)}
                    >
                      <span className="chapter-emoji" aria-hidden="true">{t.emoji}</span>
                      <span className="chapter-item-text">
                        <span className="chapter-item-label">
                          <span className="chapter-no">{String(i + 1).padStart(2, '0')}</span> {t.label}
                        </span>
                        <span className="chapter-item-count">
                          {(topicEntries.get(t.slug) || []).length} stories
                        </span>
                      </span>
                      <span className="chapter-item-arrow" aria-hidden="true">›</span>
                    </button>
                  ))}
                </nav>
              ) : (
                <nav className="chapter-list" aria-label="Years">
                  {years.map(([y, list]) => (
                    <button
                      key={y}
                      className={`chapter-item${y === selYear ? ' selected' : ''}`}
                      onClick={() => select('year', y)}
                    >
                      <span className="chapter-year" aria-hidden="true">{y.slice(2)}</span>
                      <span className="chapter-item-text">
                        <span className="chapter-item-label">{y}</span>
                        <span className="chapter-item-count">
                          {list.length} stories · pages {pageNo.get(list[0].id)}–{pageNo.get(list[list.length - 1].id)}
                        </span>
                      </span>
                      <span className="chapter-item-arrow" aria-hidden="true">›</span>
                    </button>
                  ))}
                </nav>
              )}

              <footer className="toc-tips">
                <span><kbd>←</kbd><kbd>→</kbd> turn pages</span>
                <span><kbd>[</kbd><kbd>]</kbd> within chapter</span>
                <span><kbd>C</kbd> contents</span>
                <span><kbd>/</kbd> search</span>
              </footer>
            </div>
            <div className="folio folio-left">Groth Adventures</div>
          </div>

          <div className="spine" aria-hidden="true" />

          <div className="page recto">
            <div className="page-inner">
              {view === 'chapters' && chapterInfo ? (
                <>
                  <header className="toc-header detail">
                    <p
                      className="chapter-eyebrow"
                      style={{ color: chapterInfo.color || 'var(--brown)' }}
                    >
                      {chapterInfo.emoji} Chapter {visibleTopics.findIndex((t) => t.slug === selChapter) + 1}
                    </p>
                    <h2 className="toc-heading">{chapterInfo.label}</h2>
                    <p className="toc-subheading">{chapterInfo.tagline}</p>
                  </header>
                  <div className="toc-rows">
                    {chapterDetail.map((e) => <EntryRow key={e.id} e={e} />)}
                  </div>
                </>
              ) : (
                <>
                  <header className="toc-header detail">
                    <p className="chapter-eyebrow">The year</p>
                    <h2 className="toc-heading">{selYear}</h2>
                    <p className="toc-subheading">{yearDetail.length} stories</p>
                  </header>
                  {monthGroups.map(([month, list]) => (
                    <section key={month} className="toc-month">
                      <h3 className="toc-month-heading">{month}</h3>
                      <div className="toc-rows">
                        {list.map((e) => <EntryRow key={e.id} e={e} />)}
                      </div>
                    </section>
                  ))}
                </>
              )}
            </div>
            <div className="folio folio-right">{entries.length} pages</div>
          </div>
        </div>
      </div>
    </div>
  )
}
