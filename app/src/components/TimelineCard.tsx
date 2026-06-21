import { Link } from 'react-router-dom'
import TagChip from './TagChip'

interface Tag {
  slug: string
  label: string
  category: string
  color?: string | null
}

interface Hero {
  url: string
  sha256: string
  ext: string
  width?: number
  height?: number
  alt_text?: string
}

interface TimelineCardProps {
  id: number
  title: string
  event_date?: string | null
  summary?: string
  hero?: Hero | null
  tags?: Tag[]
  side?: 'left' | 'right'
}

export default function TimelineCard({
  id,
  title,
  event_date,
  summary,
  hero,
  tags = [],
  side = 'left',
}: TimelineCardProps) {
  const formattedDate = event_date
    ? new Date(event_date + 'T12:00:00').toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : null

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: side === 'left' ? 'flex-start' : 'flex-end',
        padding: '0 var(--space-8)',
        position: 'relative',
      }}
    >
      <div
        className="paper"
        style={{
          maxWidth: '480px',
          width: '100%',
          padding: 'var(--space-5)',
          borderRadius: 'var(--radius-md)',
          transition: 'transform var(--transition-fast), box-shadow var(--transition-fast)',
        }}
        onMouseEnter={(e) => {
          const el = e.currentTarget as HTMLElement
          el.style.transform = 'translateY(-2px)'
          el.style.boxShadow = 'var(--shadow-lg)'
        }}
        onMouseLeave={(e) => {
          const el = e.currentTarget as HTMLElement
          el.style.transform = ''
          el.style.boxShadow = ''
        }}
      >
        {/* Hero image */}
        {hero && (
          <Link to={`/entry/${id}`} style={{ display: 'block', marginBottom: 'var(--space-4)' }}>
            <div
              style={{
                borderRadius: 'var(--radius-sm)',
                overflow: 'hidden',
                aspectRatio: '16/9',
                background: 'var(--color-parchment)',
              }}
            >
              <img
                src={hero.url}
                alt={hero.alt_text || title}
                loading="lazy"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>
          </Link>
        )}

        {/* Date */}
        {formattedDate && (
          <p
            style={{
              fontFamily: 'var(--font-ui)',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--color-accent-red)',
              marginBottom: 'var(--space-2)',
            }}
          >
            {formattedDate}
          </p>
        )}

        {/* Title */}
        <h3 style={{ fontSize: 'var(--text-xl)', marginBottom: 'var(--space-3)' }}>
          <Link
            to={`/entry/${id}`}
            style={{ color: 'var(--color-heading)', textDecoration: 'none' }}
            onMouseEnter={(e) => ((e.target as HTMLElement).style.color = 'var(--color-accent-red)')}
            onMouseLeave={(e) => ((e.target as HTMLElement).style.color = 'var(--color-heading)')}
          >
            {title}
          </Link>
        </h3>

        {/* Summary */}
        {summary && (
          <p
            style={{
              fontSize: 'var(--text-sm)',
              color: 'var(--color-text-muted)',
              lineHeight: 'var(--leading-relaxed)',
              marginBottom: 'var(--space-4)',
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {summary}
          </p>
        )}

        {/* Tags */}
        {tags.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-1)' }}>
            {tags.slice(0, 6).map((t) => (
              <TagChip key={t.slug} {...t} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
