import { Link } from 'react-router-dom'

interface PolaroidThumbProps {
  entryId: number
  title: string
  date?: string | null
  imageUrl?: string | null
  alt?: string
  rotation?: number
}

export default function PolaroidThumb({
  entryId,
  title,
  date,
  imageUrl,
  alt = '',
  rotation = 0,
}: PolaroidThumbProps) {
  const formattedDate = date
    ? new Date(date + 'T12:00:00').toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : null

  return (
    <Link
      to={`/entry/${entryId}`}
      style={{
        display: 'block',
        textDecoration: 'none',
        transform: `rotate(${rotation}deg)`,
        transition: 'transform var(--transition-base), box-shadow var(--transition-base)',
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLElement
        el.style.transform = 'rotate(0deg) scale(1.04)'
        el.style.zIndex = '10'
        el.style.boxShadow = 'var(--shadow-lg)'
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement
        el.style.transform = `rotate(${rotation}deg) scale(1)`
        el.style.zIndex = ''
        el.style.boxShadow = ''
      }}
    >
      <div
        style={{
          background: 'var(--polaroid-bg)',
          border: 'var(--polaroid-border)',
          boxShadow: 'var(--polaroid-shadow)',
          padding: '10px 10px 32px 10px',
          borderRadius: '1px',
          position: 'relative',
        }}
      >
        {/* Photo area */}
        <div
          style={{
            width: '160px',
            height: '160px',
            background: 'var(--color-parchment)',
            overflow: 'hidden',
            position: 'relative',
          }}
        >
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={alt || title}
              loading="lazy"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />
          ) : (
            <div
              style={{
                width: '100%',
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '2.5rem',
                color: 'var(--color-brown-light)',
              }}
            >
              📷
            </div>
          )}
        </div>

        {/* Caption area */}
        <div style={{ marginTop: '6px', textAlign: 'center' }}>
          <p
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '0.7rem',
              fontWeight: 600,
              color: 'var(--color-ink)',
              lineHeight: 1.3,
              maxHeight: '2.6em',
              overflow: 'hidden',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
            }}
          >
            {title}
          </p>
          {formattedDate && (
            <p
              style={{
                fontFamily: 'var(--font-ui)',
                fontSize: '0.6rem',
                color: 'var(--color-text-muted)',
                marginTop: '2px',
              }}
            >
              {formattedDate}
            </p>
          )}
        </div>
      </div>
    </Link>
  )
}
