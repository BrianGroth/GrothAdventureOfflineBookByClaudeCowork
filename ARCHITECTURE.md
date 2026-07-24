# Groth Adventures Offline Scrapbook — Architecture

> **Status: built and in use (July 2026).** The plan below was the original
> design; this section records what actually shipped and where it diverged.
> See also `PRD.md` §0 for the as-built addendum.

## As-built summary

| Area | Planned | Shipped |
|---|---|---|
| Presentation | Home + Timeline + Entry pages, "scrapbook" styling | **A book**: leather cover → two-page spreads, one spread per post, 3D page-turn |
| Table of contents | By year; by trip/topic | **Two TOCs** — By Chapter (12 curated topics) and By Date (year → month), both with page numbers |
| Navigation | Prev/next chronological | Prev/next **by date** (`←`/`→`) *and* **within chapter** (`[`/`]`), plus return-to-contents and auto-bookmark |
| Distribution | Local server only | Local server **plus a static export** that runs from a folder with no server, no install, no internet |
| Operation | CLI commands | Two double-clickable scripts: `InitialRun.cmd`, `Update.cmd` |
| Archive size | ~1,700 posts est. from 2004 | **999 posts, 3,077 photos, Aug 2013 – May 2026** (see "Ingestion reality check") |

### What the book is

One blog post = one two-page spread. Photographs sit on the left (verso) page as
tilted polaroids; the story sits on the right (recto) with a drop cap, running
heads, and folios. Chapters are curated topics stored as tags, so a post's
"chapter thread" is a second axis of navigation independent of the calendar.

### Dual-mode frontend

The same build serves two very different delivery modes:

1. **Served mode** — `scrapbook serve` on `localhost:8420`; the app calls
   `/api/book/toc`, `/api/entries/{id}`, `/api/search`.
2. **Static mode** — `scrapbook export --format static-book` writes a folder
   whose `index.html` opens directly from disk (`file://`).

Static mode drove three architectural constraints:

- **Single-file build.** Browsers refuse to load external module scripts on
  `file://`, so `vite-plugin-singlefile` inlines all JS, CSS, and fonts into one
  `index.html`. Fonts therefore live in `app/src/fonts/` (bundled), not
  `app/public/`.
- **Hash routing.** `HashRouter` (`#/page/5`) needs no server-side URL rewriting.
- **Scripts, not fetch.** `fetch()` is blocked on `file://`, so the exporter
  writes data as classic `<script>` files that assign to globals: `boot.js`
  (flag + full TOC), `book-data/entries/<id>.js` (one per post, loaded on
  demand), and `book-data/search.js` (text index for in-browser search).

`app/src/book/staticData.ts` detects the mode; `BookContext` and `SearchOverlay`
branch on it. Everything else in the UI is mode-agnostic.

### Incremental everywhere

Both the sync and the export are incremental, which is what makes the monthly
routine cheap:

- **Sync** compares the blog's post list against local `source_entry_id`s and
  fetches only what's new.
- **Export** names photos by content hash, so re-exporting into an existing book
  folder copies only new images. Measured: full export several minutes, refresh
  **~9 seconds**.

### Ingestion reality check

The PRD estimated ~1,700 posts back to December 2004 from the site's archive
widget. Measured against the live site:

- `sitemap.xml` is a **single flat sitemap containing 2,329 URLs**, of which
  **999 are posts** (the rest are `wp-content/uploads` media). All 999 are
  archived locally — verified zero missing.
- WordPress.com appears to **cap the sitemap at 1,000 URLs**, so it exposes only
  the most recent posts. The oldest listed post is **2013-08-24**.
- **Posts older than that still exist** — `/2004/`, `/2008/`, `/2011/`, `/2012/`
  archive pages all return real posts — but they are not discoverable via the
  sitemap.

The connector only falls back to `_walk_archives()` when the sitemap yields
*nothing*, so today those older posts are never discovered. A read-only crawl of
monthly archives on 2026-07-24 measured the gap: **699 posts missing**, from
`2004/12/02` to `2013/08/21`, peaking at 132 posts in 2007.

**999 ingested + 699 missing = 1,698**, matching the PRD's independent estimate
of ~1,698 posts almost exactly. The book therefore holds roughly **59% of the
blog** — everything since August 2013, but nothing from the nine years before it.

Closing the gap means walking year/month archives *in addition to* the sitemap
and merging on canonical permalink, then a multi-hour backfill.
**Known limitation, not yet implemented.**

### Operational hazard fixed: multiple project copies

`pip install -e .` binds the `scrapbook` command to whichever copy of the repo
installed it, and `core/config.py` resolves the data directory relative to that
installed code. With two clones on one machine, CLI steps and script steps could
act on different archives. Both `.cmd` files now set `SCRAPBOOK_DATA_DIR` to
their own folder and invoke `python -m core.cli` (local code), and
`scripts/assign_topics.py` honours the same variable.

---

## Vision
Build a **local-first scrapbook application** that periodically imports content from `grothadventures.com`, stores it in a durable local archive, and presents it as a rich, browsable offline experience with:

- Year/month table of contents
- Topic/location/person tags
- Timeline and map views
- Strong photo-first storytelling
- Repeatable “sync every few months” workflow

This system should support adding **new sources later** (photo libraries, scanned albums, other sites) without changing core UX.

---

## Product principles
1. **Offline-first by design**: everything needed to browse is local.
2. **Single-PC operation**: runs on your own computer, no hosted server required.
3. **Idempotent imports**: rerunning import does not duplicate content.
4. **Source preservation**: keep raw source snapshots for audit/reprocessing.
5. **Curation over automation**: allow manual editing/tagging/corrections.
6. **Extensible ingestion**: adapters for WordPress now; more connectors later.
7. **Simple operations**: one command to sync, one command to run app.

---

## Recommended architecture

### 1) App layers

#### A. Ingestion layer (connectors)
- Fetches from specific sources.
- Initial connector: `wordpress-grothadventures`.
- Future connectors: Google Photos export, Apple Photos export, local folder scan, scanned documents.

#### B. Normalization layer
- Converts source-specific records into a unified domain schema.
- Handles:
  - canonical IDs
  - title/body extraction
  - post date and timezone
  - media asset extraction
  - dedupe hashing

#### C. Storage layer
- **SQLite** (metadata DB)
- **Filesystem object store** (media + raw snapshots)

#### D. Application layer
- Local web app (desktop-like) for browsing and curation.
- Full-text search, TOC, filters, slideshows.

#### E. Packaging layer
- Exports static “vault bundle” for long-term preservation/backups.

---

## Tech stack (pragmatic)

### Local runner + jobs (no hosted backend)
- **Python CLI first** with Typer (`scrapbook sync`, `scrapbook reindex`, `scrapbook export`).
- Optional **local-only API** (FastAPI on `localhost`) for richer UI workflows.
- **SQLAlchemy + Alembic** for DB and migrations.
- Important: this runs on your PC only; there is no cloud deployment requirement.

### Frontend
- **React + Vite** (or SvelteKit if you prefer minimalism)
- UI libraries optional; prioritize custom scrapbook look.

### Storage
- **SQLite** for all structured data.
- Media files in `data/media/` organized by content hash.
- Raw source snapshots in `data/raw/`.

### Search
- Start with **SQLite FTS5**.
- Optional upgrade later to Tantivy/Meilisearch if needed.

---

## Domain model (core entities)

- `Source`
  - `id`, `type`, `name`, `config_json`
- `IngestRun`
  - `id`, `source_id`, `started_at`, `completed_at`, `status`, `stats_json`
- `Entry` (story/post/event)
  - `id`, `canonical_slug`, `title`, `body_html`, `body_text`, `event_date`, `created_at`, `updated_at`, `source_url`, `source_entry_id`
- `Media`
  - `id`, `sha256`, `mime_type`, `width`, `height`, `duration_sec`, `exif_json`, `storage_path`
- `EntryMedia`
  - `entry_id`, `media_id`, `position`, `caption`, `is_cover`
- `Tag`
  - `id`, `name`, `type` (`topic`, `person`, `place`, `trip`, `custom`)
- `EntryTag`
  - `entry_id`, `tag_id`
- `Location`
  - `id`, `name`, `lat`, `lng`, `country`, `place_id`
- `EntryLocation`
  - `entry_id`, `location_id`
- `Collection`
  - user-curated albums/chapters

Add FTS virtual table over `Entry(title, body_text)`.

---

## Filesystem layout

As built:

```text
/GrothAdventureOfflineBookByClaudeCowork
  InitialRun.cmd       # double-click: full first build (install → sync → chapters → build → export)
  Update.cmd           # double-click: new posts → chapters → refresh book folder
  run.cmd              # status + serve
  /app                 # React frontend (the book)
    /src
      /book            # BookContext.tsx (state, nav), staticData.ts (file:// mode)
      /pages           # Cover.tsx, Contents.tsx, PageSpread.tsx
      /components      # SearchOverlay.tsx, PhotoLightbox.tsx
      /fonts           # bundled woff2 — inlined into the single-file build
      /styles/theme.css
    /dist              # build output: ONE self-contained index.html
  /core
    cli.py             # Typer CLI
    config.py          # paths; honours SCRAPBOOK_DATA_DIR
    static_export.py   # writes the standalone book folder
    /api               # FastAPI app + routers (book.py serves the TOC)
    /connectors        # wordpress.py
    /db                # models + migrations
  /data                # NOT in git — the archive itself (~11.5 GB)
    /db/scrapbook.sqlite
    /raw               # immutable HTML snapshots
    /media             # content-addressed photo store
    /exports/static-book   # the shareable book folder (~5.7 GB)
  /config/sources.yaml
  /scripts
    assign_topics.py   # chapter curation (curated slugs + keyword rules)
    monthly_update.ps1|sh
```

Thumbnails were never needed — the UI scales full images and lazy-loads them.

---


## Deployment model (for your question)

Yes — everything can run from your local PC.

- **No hosted server is required.**
- During use, you run either:
  1. a desktop-like app, or
  2. a local web app opened in your browser at `localhost`.
- The only network dependency is during `sync`, when downloading new content from `grothadventures.com`.
- Browsing, search, and curation should all work fully offline once synced.

---

## Ingestion strategy for grothadventures.com (phase 1)

### Connector behavior
1. Read sitemap(s) and/or WordPress REST API if available.
2. Build candidate URL list.
3. For each URL:
   - fetch canonical page
   - extract structured content (`title`, `date`, `article html`, image URLs)
   - save raw HTML snapshot
   - normalize to `Entry`
4. Download media assets.
5. Compute SHA-256; dedupe by hash.
6. Rewire entry content to local media references.
7. Upsert entry + link media + auto-tags.

### Idempotency rules
- Unique key: `(source_id, source_entry_id)` when available.
- Fallback key: normalized URL canonicalization + title/date fingerprint.
- If source changes, version entry (`updated_at`) and keep prior snapshot.

### Tagging
- Start with:
  - heuristics from title/body keyword dictionaries
  - date-based tags (`2024`, `Spring 2024`)
- Then add manual curation UI (most important).

---

## UX blueprint (offline scrapbook)

> **Superseded by the book UI — kept for historical context.** The Home /
> Timeline / Entry / Search pages below were built, then replaced. What shipped
> is described under "As-built summary" above and in the surfaces list that
> follows this block.

### Original main surfaces
1. **Home / Table of Contents** — by year, trip/collection, topic/people/places
2. **Timeline** — chronological stream with cover photos
3. **Entry page** — story text + image gallery + metadata/tags
4. **Map view** (optional in v1, ideal in v2)
5. **Search page** — text search + faceted filters
6. **Curate mode** — edit title/date, tags, media order, cover image

### Shipped surfaces (the book)
1. **Cover** (`/`) — closed book; opens to contents, or resumes at the
   auto-saved bookmark.
2. **Contents** (`/contents`) — one spread with index tabs switching between
   **By Chapter** and **By Date**; chapter/year list on the verso, entries with
   dotted leaders and page numbers on the recto.
3. **Page spread** (`/page/:id`) — photos verso, story recto; edge zones and
   arrow keys turn pages by date; `[`/`]` follow the chapter thread; `C`/`Esc`
   return to contents.
4. **Search overlay** — `/` or `Ctrl+K`, results cite page numbers.
5. **Lightbox** — click any photo; click it again (or `Esc`) to close.

Curate mode and map view remain unbuilt. Chapter curation is currently done by
editing `scripts/assign_topics.py` rather than in the UI.

### Visual style guidance
- Parchment/polaroid aesthetic on a dark leather-and-desk backdrop.
- Large photography; serif typography (Playfair Display / Lora / Inter).
- Book metaphors throughout: folios, running heads, index tabs, ribbon bookmark.
- Keyboard navigation everywhere; `prefers-reduced-motion` disables page-turn
  animation.
- Under 920px the spread folds into a single scrolling page with fixed controls.

---

## Operations workflow (the every-few-month routine)

As built, this is one double-click — `Update.cmd` (optionally with a destination
folder) runs:

1. `python -m core.cli sync --source grothadventures` — new posts only
2. `python scripts/assign_topics.py` — re-file chapters; prints anything that
   needs a hand-assigned chapter
3. `python -m core.cli export --format static-book` — refresh the book folder
   (new photos only, ~9s)

`InitialRun.cmd` is the same flow plus dependency install, DB init, and the
frontend build, for a machine starting from nothing.

The original `scrapbook review` curate-queue step was never built; chapter
corrections are made in `scripts/assign_topics.py`.

---

## Security and preservation

- No cloud dependency required to browse.
- Checksums for media integrity.
- Immutable raw snapshots for traceability.
- Export a self-contained archive bundle with manifest.
- Optional signed manifest for long-term authenticity.

---

## Migration plan from current repo

### Phase 0 (1 week): Foundation
- Create monorepo structure (`core`, `app`, `data`).
- Set up CLI + SQLite + migrations.
- Add optional local-only API scaffold (if needed for UI).

### Phase 1 (1–2 weeks): Ingest + browse MVP
- Build `grothadventures` connector.
- Ingest entries/media into local store.
- Basic TOC + Entry page + search.
- Ensure fully offline media serving.

### Phase 2 (1 week): Curation + quality
- Add manual editing/tagging UI.
- Improve dedupe rules and conflict resolution.
- Add import diagnostics and report.

### Phase 3 (1 week): Scrapbook polish
- Theme/styling pass.
- Timeline view and richer galleries.
- Keyboard navigation and slideshow.

### Phase 4 (later): Additional sources
- Implement photo-library connector(s).
- Add scanned-album ingestion pipeline.

---

## Definition of done for v1 — scorecard

| Criterion | Status |
|---|---|
| One command ingests latest site posts | ✅ `Update.cmd` (double-click) |
| App works completely offline | ✅ served **and** as a standalone folder |
| Table of contents by year + topic | ✅ both, with page numbers |
| Entries include local-cached media | ✅ 3,077 photos, content-addressed |
| Manually curate metadata/tags | ⚠️ via `scripts/assign_topics.py`, no UI |
| Export and back up a complete bundle | ✅ `--format bundle` and `--format static-book` |

---

## Known gaps / next steps

1. **699 pre-2013 posts are not ingested** (measured, see above). The sitemap
   caps at ~1,000 URLs, hiding nine years of earlier posts that still exist on
   the site. Fix: always walk year/month archives and merge with sitemap
   results, instead of using the archive walk only as a fallback. This is the
   largest open item — the difference between "the whole blog" and "the blog
   since August 2013".
2. **Curate mode.** No in-app editing of titles, dates, chapters, or covers;
   chapter changes mean editing a Python dict and re-running a script.
3. **Map view.** Never started; `Location`/`EntryLocation` tables exist unused.
4. **Additional connectors** (photo libraries, scanned albums) — Phase 4, untouched.
5. **Thumbnails.** Full-size images are served to the grid; fine at this scale,
   but a derivative pipeline would cut the 5.7 GB export considerably.
