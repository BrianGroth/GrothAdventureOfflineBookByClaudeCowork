import { Link } from 'react-router-dom'

interface TagChipProps {
  slug: string
  label: string
  category?: string
  color?: string | null
  clickable?: boolean
  size?: 'sm' | 'md'
}

const CATEGORY_COLORS: Record<string, string> = {
  year: '#8b6f4e',
  season: '#16a085',
  location: '#2980b9',
  person: '#8e44ad',
  keyword: '#c0392b',
  collection: '#d4a017',
}

export default function TagChip({
  slug,
  label,
  category = 'keyword',
  color,
  clickable = true,
  size = 'sm',
}: TagChipProps) {
  const bgColor = color || CATEGORY_COLORS[category] || '#8b6f4e'

  const style: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontFamily: 'var(--font-ui)',
    fontSize: size === 'sm' ? '0.7rem' : '0.8rem',
    fontWeight: 600,
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    padding: size === 'sm' ? '2px 8px' : '3px 10px',
    borderRadius: '999px',
    background: bgColor + '18',
    color: bgColor,
    border: `1px solid ${bgColor}30`,
    textDecoration: 'none',
    whiteSpace: 'nowrap',
    transition: 'all 150ms ease',
    cursor: clickable ? 'pointer' : 'default',
  }

  if (!clickable) {
    return <span style={style}>{label}</span>
  }

  return (
    <Link
      to={`/search?tag=${encodeURIComponent(slug)}`}
      style={style}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLElement
        el.style.background = bgColor + '28'
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement
        el.style.background = bgColor + '18'
      }}
    >
      {label}
    </Link>
  )
}
