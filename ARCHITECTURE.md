# Groth Adventures Offline Scrapbook — Rearchitecture Plan

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

```text
/adventures-scrapbook
  /app                 # frontend
  /core                # CLI + ingestion + models (+ optional local API)
  /data
    /db
      scrapbook.sqlite
    /raw               # raw downloaded payloads (json/html)
    /media             # content-addressed media store
    /thumbnails
    /exports
  /config
    sources.yaml
  /scripts
```

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

### Main surfaces
1. **Home / Table of Contents**
   - By Year
   - By Trip/Collection
   - By Topic/People/Places
2. **Timeline**
   - chronological stream with cover photos
3. **Entry page**
   - story text + image gallery + metadata/tags
4. **Map view** (optional in v1, ideal in v2)
5. **Search page**
   - text search + faceted filters
6. **Curate mode**
   - edit title/date
   - add/remove tags
   - reorder media
   - define cover image

### Visual style guidance
- Parchment/polaroid aesthetic.
- Large photography; serif typography.
- “Cabinet” metaphors (collections, chapters, trips).
- Keep keyboard nav and slideshow controls.

---

## Operations workflow (your every-few-month routine)

1. `scrapbook sync --source grothadventures`
2. `scrapbook review` (open app in curate queue)
3. Approve/adjust tags and covers.
4. `scrapbook export --format bundle`
5. Backup `/data` to external drive/cloud.

Automate with one script:
- `scripts/monthly_update.(ps1|sh)`

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

## Definition of done for v1

- You can run one command and ingest latest site posts.
- App works completely offline.
- Table of contents by year + topic exists.
- Entries include local-cached media.
- You can manually curate metadata/tags.
- You can export and back up a complete bundle.

---

## Immediate next steps (what I would do first)

1. Finalize stack choice:
   - Python/Typer/React/SQLite (with optional local FastAPI)
2. Scaffold project skeleton.
3. Implement DB schema + migrations.
4. Implement `grothadventures` connector with raw snapshot storage.
5. Build minimal UI: TOC + Entry + Search.
6. Add one-command sync and export scripts.

If you want, I can execute this next by creating the actual skeleton and first connector in this repo.
