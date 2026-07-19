import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  ReactNode,
} from 'react'
import { isStaticBook, staticToc, staticEntry } from './staticData'

/* ── Types ────────────────────────────────────── */

export interface TocTopic {
  slug: string
  label: string
  emoji: string
  tagline: string
  color: string | null
  order: number
}

export interface TocEntry {
  id: number
  title: string
  event_date: string | null
  topic: string
  photos: number
  snippet: string
  keywords: string[]
  cover: { url: string; width?: number; height?: number } | null
}

export interface MediaItem {
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

export interface EntryDetail {
  id: number
  title: string
  event_date?: string | null
  author?: string | null
  summary?: string
  html_content: string
  permalink: string
  media: MediaItem[]
}

export interface PageNav {
  entry: TocEntry
  pageNo: number
  total: number
  prevDate: TocEntry | null
  nextDate: TocEntry | null
  topic: TocTopic | null
  topicIndex: number
  topicCount: number
  prevTopic: TocEntry | null
  nextTopic: TocEntry | null
}

interface BookState {
  loading: boolean
  error: string | null
  topics: TocTopic[]
  entries: TocEntry[] // book order: chronological
  byId: Map<number, TocEntry>
  pageNo: Map<number, number>
  topicEntries: Map<string, TocEntry[]>
  topicBySlug: Map<string, TocTopic>
  navFor: (id: number) => PageNav | null
  getEntry: (id: number) => Promise<EntryDetail>
  prefetchEntry: (id: number) => void
}

const BookContext = createContext<BookState | null>(null)

/* ── Bookmark (ribbon) helpers ────────────────── */

const BOOKMARK_KEY = 'groth-book-bookmark'

export function saveBookmark(id: number, title: string) {
  try {
    localStorage.setItem(BOOKMARK_KEY, JSON.stringify({ id, title }))
  } catch {
    /* private mode etc. */
  }
}

export function getBookmark(): { id: number; title: string } | null {
  try {
    const raw = localStorage.getItem(BOOKMARK_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

/* ── Provider ─────────────────────────────────── */

export function BookProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [topics, setTopics] = useState<TocTopic[]>([])
  const [entries, setEntries] = useState<TocEntry[]>([])
  const detailCache = useRef(new Map<number, Promise<EntryDetail>>())

  useEffect(() => {
    // Static-book mode (USB/folder copy): the TOC was baked into the page
    // by the exporter's boot.js — no server, no fetch.
    const baked = staticToc()
    if (baked) {
      setTopics(baked.topics)
      setEntries(baked.entries)
      setLoading(false)
      return
    }
    fetch('/api/book/toc')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data) => {
        setTopics(data.topics)
        setEntries(data.entries)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const derived = useMemo(() => {
    const byId = new Map<number, TocEntry>()
    const pageNo = new Map<number, number>()
    const topicEntries = new Map<string, TocEntry[]>()
    const topicBySlug = new Map<string, TocTopic>()

    topics.forEach((t) => {
      topicBySlug.set(t.slug, t)
      topicEntries.set(t.slug, [])
    })
    entries.forEach((e, i) => {
      byId.set(e.id, e)
      pageNo.set(e.id, i + 1)
      if (!topicEntries.has(e.topic)) topicEntries.set(e.topic, [])
      topicEntries.get(e.topic)!.push(e)
    })
    return { byId, pageNo, topicEntries, topicBySlug }
  }, [topics, entries])

  const navFor = (id: number): PageNav | null => {
    const entry = derived.byId.get(id)
    if (!entry) return null
    const idx = derived.pageNo.get(id)! - 1
    const chapter = derived.topicEntries.get(entry.topic) || []
    const tIdx = chapter.findIndex((e) => e.id === id)
    return {
      entry,
      pageNo: idx + 1,
      total: entries.length,
      prevDate: idx > 0 ? entries[idx - 1] : null,
      nextDate: idx < entries.length - 1 ? entries[idx + 1] : null,
      topic: derived.topicBySlug.get(entry.topic) || null,
      topicIndex: tIdx + 1,
      topicCount: chapter.length,
      prevTopic: tIdx > 0 ? chapter[tIdx - 1] : null,
      nextTopic: tIdx >= 0 && tIdx < chapter.length - 1 ? chapter[tIdx + 1] : null,
    }
  }

  const getEntry = (id: number): Promise<EntryDetail> => {
    if (!detailCache.current.has(id)) {
      const p = isStaticBook()
        ? staticEntry(id)
        : fetch(`/api/entries/${id}`).then((r) => {
            if (!r.ok) {
              detailCache.current.delete(id)
              throw new Error(`HTTP ${r.status}`)
            }
            return r.json()
          })
      detailCache.current.set(id, p)
    }
    return detailCache.current.get(id)!
  }

  const prefetchEntry = (id: number) => {
    getEntry(id).then((d) => {
      // Warm the image cache for the lead photo so page flips land instantly.
      if (d.media?.[0]) {
        const img = new Image()
        img.src = d.media[0].url
      }
    }).catch(() => { /* prefetch is best-effort */ })
  }

  const value: BookState = {
    loading,
    error,
    topics,
    entries,
    ...derived,
    navFor,
    getEntry,
    prefetchEntry,
  }

  return <BookContext.Provider value={value}>{children}</BookContext.Provider>
}

export function useBook(): BookState {
  const ctx = useContext(BookContext)
  if (!ctx) throw new Error('useBook must be used inside BookProvider')
  return ctx
}

/* ── Small shared helpers ─────────────────────── */

export function formatDate(date: string | null | undefined, style: 'long' | 'short' | 'month' = 'long'): string {
  if (!date) return ''
  const d = new Date(date + 'T12:00:00')
  if (style === 'short') {
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }
  if (style === 'month') {
    return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  }
  return d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
}

export const prefersReducedMotion = () =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches
