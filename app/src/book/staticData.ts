/* Static-book mode: data access without a server.
 *
 * The `scrapbook export --format static-book` command writes the whole book
 * into a folder: this app as one index.html, photos under media/, and the
 * data as plain JS files under book-data/. Browsers block fetch() on file://
 * pages, but classic <script> tags load fine — so every data file is a
 * script that assigns to a window global, and this module loads them.
 *
 * boot.js (injected into index.html by the exporter) sets:
 *   window.__BOOK_STATIC__ = true
 *   window.__BOOK_TOC__    = { topics, entries }   (same shape as /api/book/toc)
 * book-data/entries/<id>.js sets window.__BOOK_ENTRIES__[<id>]
 * book-data/search.js sets window.__BOOK_SEARCH__ = [{id, title, event_date, text}]
 */

import type { EntryDetail, TocEntry, TocTopic } from './BookContext'

interface BookWindow extends Window {
  __BOOK_STATIC__?: boolean
  __BOOK_TOC__?: { topics: TocTopic[]; entries: TocEntry[] }
  __BOOK_ENTRIES__?: Record<number, EntryDetail>
  __BOOK_SEARCH__?: { id: number; title: string; event_date: string | null; text: string }[]
}

const win = window as BookWindow

export function isStaticBook(): boolean {
  return win.__BOOK_STATIC__ === true
}

export function staticToc(): { topics: TocTopic[]; entries: TocEntry[] } | null {
  return win.__BOOK_TOC__ ?? null
}

/* ── Classic-script loader (works on file://) ── */

const loaded = new Map<string, Promise<void>>()

function loadScript(src: string): Promise<void> {
  if (!loaded.has(src)) {
    loaded.set(
      src,
      new Promise((resolve, reject) => {
        const el = document.createElement('script')
        el.src = src
        el.onload = () => resolve()
        el.onerror = () => {
          loaded.delete(src)
          reject(new Error(`Could not load ${src}`))
        }
        document.head.appendChild(el)
      }),
    )
  }
  return loaded.get(src)!
}

export async function staticEntry(id: number): Promise<EntryDetail> {
  await loadScript(`book-data/entries/${id}.js`)
  const entry = win.__BOOK_ENTRIES__?.[id]
  if (!entry) throw new Error(`Entry ${id} missing from static data`)
  return entry
}

/* ── Client-side search over the baked text index ── */

export interface StaticSearchResult {
  id: number
  title: string
  event_date: string | null
  snippet: string
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export async function staticSearch(query: string, limit = 12): Promise<StaticSearchResult[]> {
  await loadScript('book-data/search.js')
  const index = win.__BOOK_SEARCH__ || []
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (words.length === 0) return []

  const scored: { score: number; id: number; title: string; event_date: string | null; snippet: string }[] = []

  for (const item of index) {
    const titleLower = item.title.toLowerCase()
    const textLower = item.text.toLowerCase()
    if (!words.every((w) => titleLower.includes(w) || textLower.includes(w))) continue

    let score = 0
    let firstHit = -1
    for (const w of words) {
      if (titleLower.includes(w)) score += 10
      const pos = textLower.indexOf(w)
      if (pos >= 0) {
        score += 1
        if (firstHit < 0 || pos < firstHit) firstHit = pos
      }
    }

    // Snippet: a window of text around the first match, with matches marked.
    let snippet = ''
    if (firstHit >= 0) {
      const start = Math.max(0, firstHit - 50)
      const end = Math.min(item.text.length, firstHit + 110)
      snippet = (start > 0 ? '…' : '') + item.text.slice(start, end) + (end < item.text.length ? '…' : '')
    } else {
      snippet = item.text.slice(0, 140)
    }
    snippet = escapeHtml(snippet)
    for (const w of words) {
      snippet = snippet.replace(new RegExp(`(${escapeRegExp(w)})`, 'gi'), '<mark>$1</mark>')
    }

    scored.push({ score, id: item.id, title: item.title, event_date: item.event_date, snippet })
  }

  scored.sort((a, b) => b.score - a.score)
  return scored.slice(0, limit)
}
