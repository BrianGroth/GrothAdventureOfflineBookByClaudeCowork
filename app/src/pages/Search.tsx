import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import TagChip from '../components/TagChip'

interface SearchResult {
  id: number
  title: string
  event_date?: string | null
  summary?: string
  permalink?: string
  snippet?: string
  hero?: { url: string; sha256: string; ext: string } | null
}

interface Tag {
  id: number
  slug: string
  label: string
  category: string
  color?: string | null
  count: number
}

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialQuery = searchParams.get('q') || ''
  const initialTag = searchParams.get('tag') || ''

  const [query, setQuery] = useState(initialQuery)
  const [activeTag, setActiveTag] = useState(initialTag)
  const [results, setResults] = useState<SearchResult[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [tags, setTags] = useState<Tag[]>([])
  const [submitted, setSubmitted] = useState(false)

  // Load tags for facet sidebar
  useEffect(() => {
    fetch('/api/tags')
      .then((r) => r.json())
      .then(setTags)
      .catch(console.error)
  }, [])

  const doSearch = useCallback(
    async (q: string, tag?: string) => {
      setLoading(true)
      setSubmitted(true)
      try {
        if (tag && !q) {
          // Tag-only browse
          const r = await fetch(`/api/tags/${encodeURIComponent(tag)}/entries?limit=50`)
          const data = await r.json()
          setResults(data.items || [])
          setTotal((data.items || []).length)
        } else if (q) {
          const params = new URLSearchParams({ q, limit: '50' })
          if (tag) params.set('tag', tag)
          const r = await fetch(`/api/search?${params}`)
          const data = await r.json()
          setResults(data.items || [])
          setTotal(data.total || 0)
        } else {
          setResults([])
          setTotal(0)
        }
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  // Run search when URL params change
  useEffect(() => {
    const q = searchParams.get('q') || ''
    const tag = searchParams.get('tag') || ''
    setQuery(q)
    setActiveTag(tag)
    if (q || tag) {
      doSearch(q, tag)
    }
  }, [searchParams, doSearch])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const params: Record<string, string> = {}
    if (query.trim()) params.q = query.trim()
    if (activeTag) params.tag = activeTag
    setSearchParams(params)
  }

  const locationTags = tags.filter((t) => t.category === 'location' && t.count > 0)
  const yearTags = tags.filter((t) => t.category === 'year' && t.count > 0)
  const keywordTags = tags.filter((t) => t.category === 'keyword' && t.count > 0)

  return (
    <div
      style={{
        maxWidth: 'var(--max-width)',
        margin: '0 auto',
        padding: 'var(--space-8) var(--space-6)',
        display: 'grid',
        gridTemplateColumns: '260px 1fr',
        gap: 'var(--space-8)',
        alignItems: 'start',
      }}
    >
      {/* Sidebar */}
      <aside>
        {/* Search form */}
        <form onSubmit={handleSubmit} style={{ marginBottom: 'var(--space-8)' }}>
          <label
            style={{
              display: 'block',
              fontFamily: 'var(--font-ui)',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--color-text-muted)',
              marginBottom: 'var(--space-2)',
            }}
          >
            Search
          </label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search adventures…"
            style={{
              width: '100%',
              fontFamily: 'var(--font-ui)',
              fontSize: 'var(--text-sm)',
              padding: 'var(--space-2) var(--space-3)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-surface)',
              color: 'var(--color-text)',
              outline: 'none',
              marginBottom: 'var(--space-2)',
            }}
          />
          <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
            Search
          </button>
        </form>

        {/* Tag facets */}
        {locationTags.length > 0 && (
          <TagFacetGroup
            title="Locations"
            tags={locationTags}
            activeTag={activeTag}
            onSelect={(slug) => {
              const newTag = activeTag === slug ? '' : slug
              setActiveTag(newTag)
              setSearchParams(query ? { q: query, tag: newTag } : newTag ? { tag: newTag } : {})
            }}
          />
        )}

        {yearTags.length > 0 && (
          <TagFacetGroup
            title="Years"
            tags={yearTags.slice(0, 15)}
            activeTag={activeTag}
            onSelect={(slug) => {
              const newTag = activeTag === slug ? '' : slug
              setActiveTag(newTag)
              setSearchParams(query ? { q: query, tag: newTag } : newTag ? { tag: newTag } : {})
            }}
          />
        )}

        {keywordTags.length > 0 && (
          <TagFacetGroup
            title="Activities & Topics"
            tags={keywordTags}
            activeTag={activeTag}
            onSelect={(slug) => {
              const newTag = activeTag === slug ? '' : slug
              setActiveTag(newTag)
              setSearchParams(query ? { q: query, tag: newTag } : newTag ? { tag: newTag } : {})
            }}
          />
        )}
      </aside>

      {/* Results */}
      <div>
        <div style={{ marginBottom: 'var(--space-6)' }}>
          <h1
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'var(--text-3xl)',
              color: 'var(--color-heading)',
              marginBottom: 'var(--space-2)',
            }}
          >
            {submitted ? 'Search Results' : 'Search Adventures'}
          </h1>
          {submitted && (
            <p style={{ fontFamily: 'var(--font-ui)', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
              {loading ? 'Searching…' : `${total} ${total === 1 ? 'result' : 'results'}`}
              {query && <> for "<strong>{query}</strong>"</>}
              {activeTag && <> tagged "<strong>{activeTag}</strong>"</>}
            </p>
          )}
        </div>

        {loading ? (
          <div className="loading-center">
            <div className="spinner" />
            <span>Searching…</span>
          </div>
        ) : !submitted ? (
          <div className="empty-state">
            <p>Enter a search term or select a tag to browse adventures.</p>
          </div>
        ) : results.length === 0 ? (
          <div className="empty-state">
            <h2>No results found</h2>
            <p>Try different keywords or browse by year or tag.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            {results.map((result) => (
              <SearchResultCard key={result.id} result={result} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function TagFacetGroup({
  title,
  tags,
  activeTag,
  onSelect,
}: {
  title: string
  tags: Tag[]
  activeTag: string
  onSelect: (slug: string) => void
}) {
  return (
    <div style={{ marginBottom: 'var(--space-6)' }}>
      <p
        style={{
          fontFamily: 'var(--font-ui)',
          fontSize: 'var(--text-xs)',
          fontWeight: 600,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: 'var(--color-text-muted)',
          marginBottom: 'var(--space-3)',
        }}
      >
        {title}
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
        {tags.map((tag) => (
          <button
            key={tag.slug}
            onClick={() => onSelect(tag.slug)}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: 'var(--space-2) var(--space-3)',
              background: activeTag === tag.slug ? 'var(--color-parchment)' : 'none',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              fontFamily: 'var(--font-ui)',
              fontSize: 'var(--text-sm)',
              color: activeTag === tag.slug ? 'var(--color-heading)' : 'var(--color-text-muted)',
              textAlign: 'left',
              fontWeight: activeTag === tag.slug ? 600 : 400,
              transition: 'all var(--transition-fast)',
            }}
            onMouseEnter={(e) => {
              if (activeTag !== tag.slug) {
                (e.currentTarget as HTMLElement).style.background = 'var(--color-parchment)'
              }
            }}
            onMouseLeave={(e) => {
              if (activeTag !== tag.slug) {
                (e.currentTarget as HTMLElement).style.background = 'none'
              }
            }}
          >
            <span>{tag.label}</span>
            <span
              style={{
                fontFamily: 'var(--font-ui)',
                fontSize: 'var(--text-xs)',
                color: 'var(--color-text-muted)',
                background: 'var(--color-parchment)',
                padding: '1px 6px',
                borderRadius: '999px',
              }}
            >
              {tag.count}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

function SearchResultCard({ result }: { result: SearchResult }) {
  const formattedDate = result.event_date
    ? new Date(result.event_date + 'T12:00:00').toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : null

  return (
    <Link
      to={`/entry/${result.id}`}
      style={{ textDecoration: 'none' }}
    >
      <div
        className="paper"
        style={{
          display: 'grid',
          gridTemplateColumns: result.hero ? '120px 1fr' : '1fr',
          gap: 'var(--space-4)',
          padding: 'var(--space-4)',
          borderRadius: 'var(--radius-md)',
          transition: 'transform var(--transition-fast), box-shadow var(--transition-fast)',
        }}
        onMouseEnter={(e) => {
          const el = e.currentTarget as HTMLElement
          el.style.transform = 'translateY(-1px)'
          el.style.boxShadow = 'var(--shadow-lg)'
        }}
        onMouseLeave={(e) => {
          const el = e.currentTarget as HTMLElement
          el.style.transform = ''
          el.style.boxShadow = ''
        }}
      >
        {result.hero && (
          <div
            style={{
              borderRadius: 'var(--radius-sm)',
              overflow: 'hidden',
              aspectRatio: '1',
              background: 'var(--color-parchment)',
            }}
          >
            <img
              src={result.hero.url}
              alt={result.title}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          </div>
        )}
        <div>
          {formattedDate && (
            <p
              style={{
                fontFamily: 'var(--font-ui)',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: 'var(--color-accent-red)',
                marginBottom: 'var(--space-1)',
              }}
            >
              {formattedDate}
            </p>
          )}
          <h3
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'var(--text-lg)',
              color: 'var(--color-heading)',
              marginBottom: 'var(--space-2)',
            }}
          >
            {result.title}
          </h3>
          {result.snippet ? (
            <p
              style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', lineHeight: 'var(--leading-relaxed)' }}
              dangerouslySetInnerHTML={{ __html: result.snippet }}
            />
          ) : result.summary ? (
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', lineHeight: 'var(--leading-relaxed)' }}>
              {result.summary}
            </p>
          ) : null}
        </div>
      </div>
    </Link>
  )
}
