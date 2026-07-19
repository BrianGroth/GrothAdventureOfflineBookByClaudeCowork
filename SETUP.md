# Groth Adventures Offline Scrapbook — Setup Guide

## Quick Start

### 1. Install Python dependencies

```powershell
# From the project root
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

### 2. Initialize the database

```powershell
scrapbook init
```

This creates `data/` in the project root with the SQLite database and subdirectories.

To use a custom data directory:
```powershell
scrapbook init --data-dir C:\Users\brian\AdventureData
```

### 3. Sync the blog

```powershell
scrapbook sync --source grothadventures
```

Options:
- `--full` — re-sync all posts (not just new ones)
- `--max-posts 20` — limit for testing
- `--no-media` — skip image downloads
- `--verbose` — show per-post progress

### 4. Build the React frontend

```powershell
cd app
npm install
npm run build
cd ..
```

### 5. Launch the scrapbook

```powershell
scrapbook serve
```

Opens http://127.0.0.1:8420 in your browser automatically.

---

## Development Mode (React hot-reload)

Run both the API server and the Vite dev server:

**Terminal 1:**
```powershell
scrapbook serve --no-browser
```

**Terminal 2:**
```powershell
cd app
npm run dev
```

Then open http://localhost:5173 — the Vite dev server proxies `/api` to the FastAPI backend.

---

## The Book UI

The app presents the blog as an offline book: a cover, a two-page spread per
blog entry, and two tables of contents — **By Chapter** (curated topics) and
**By Date** (chronological, with page numbers).

Navigation on every page:
- `←` / `→` (or the page-edge zones) — previous / next page by date
- `[` / `]` (or the chapter bar below the book) — previous / next page in the same chapter
- `C` or `Esc` — back to the table of contents
- `/` or `Ctrl+K` — search the whole book
- Your place is bookmarked automatically; the cover offers "Resume".

### Chapter (topic) assignments

Each entry belongs to one chapter, stored as `topic-*` tags
(category `collection`) in the database. After syncing new posts, re-run:

```powershell
python scripts/assign_topics.py
```

It reports any new entries that still need a chapter; add them to
`ASSIGNMENTS` in that script. Unassigned entries appear in a temporary
"New Adventures" chapter so the book keeps working either way.

---

## Monthly Update

Run the monthly update script to pull new posts:

```powershell
# Windows
.\scripts\monthly_update.ps1

# macOS/Linux
bash scripts/monthly_update.sh
```

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `scrapbook init` | Initialize database and dirs |
| `scrapbook status` | Show sync status |
| `scrapbook sync --source grothadventures` | Sync posts |
| `scrapbook serve` | Start web server |
| `scrapbook reindex --fts --tags` | Rebuild search index |
| `scrapbook export --format bundle` | Export portable backup bundle (zip) |
| `scrapbook export --format static-book` | Export a folder that opens by double-clicking index.html (USB/share) |
| `scrapbook verify-bundle path.zip` | Verify a bundle |
| `scrapbook open-bundle path.zip` | Open a bundle |

---

## Data Layout

```
data/                          # Created in project root by `scrapbook init`
├── db/
│   └── scrapbook.sqlite      # Main database
├── media/
│   └── ab/cd/abcd...jpg      # Media by SHA-256 (2/2/rest sharding)
├── raw/
│   └── 1/2024/06/15-post/    # Raw HTML snapshots
│       ├── response.html
│       └── headers.json
└── exports/
    └── scrapbook-bundle-*.zip
```

---

## Troubleshooting

**"Schema version mismatch" (exit code 3)**
Run `scrapbook init` again to apply any pending migrations.

**"Source not found in config"**
Check `config/sources.yaml` has a source with `name: grothadventures`.

**Fonts not loading**
Self-hosted fonts are bundled in `app/public/fonts/`. They are loaded offline.
If you see fallback fonts, verify the `.woff2` files exist in that directory.

**"Database not found"**
Run `scrapbook init` first before any other command.
