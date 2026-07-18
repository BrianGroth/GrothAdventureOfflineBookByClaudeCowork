# Groth Adventures — The Offline Book

A local-first archive of [grothadventures.com](https://grothadventures.com) presented as a
**page-flip book**: a leather cover opens onto two-page spreads — one spread per blog
post — with polaroid photos on the left page and the story on the right. Everything
(posts, photos, search) is stored on your own PC and works completely offline once synced.

The book has two tables of contents:

- **By Chapter** — ten curated topics (Life in the Lowlands, Adventures in Japan,
  Piper & Friends, …)
- **By Date** — chronological, grouped by year and month, with page numbers

---

## Quick start (first time on a new machine)

You need **Python 3.12+** and **Node.js 18+**.

```powershell
# 1. Install the Python package (provides the `scrapbook` CLI)
pip install -e .

# 2. Create the local database and data folders
scrapbook init

# 3. Download all blog posts and photos (needs internet, one time)
scrapbook sync --source grothadventures

# 4. Assign each post to a book chapter
python scripts/assign_topics.py

# 5. Build the web app
cd app
npm install
npm run build
cd ..

# 6. Open the book
scrapbook serve
```

`scrapbook serve` starts a local server at **http://127.0.0.1:8420** and opens it in
your browser. From here on, no internet is needed to read the book.

## Everyday use

Just run (or double-click `run.cmd`):

```powershell
scrapbook serve
```

## Getting new blog posts into the book

Every month or so, with internet:

```powershell
scrapbook sync --source grothadventures      # pull new posts + photos
python scripts/assign_topics.py              # re-apply chapters
```

The topics script prints any **new posts that don't have a chapter yet** — open
[scripts/assign_topics.py](scripts/assign_topics.py), add each new entry id to
`ASSIGNMENTS`, and run it again. (Until you do, new posts appear in a temporary
"New Adventures" chapter, so the book keeps working either way.)

There is also a one-shot script that does sync + reindex + export:
`.\scripts\monthly_update.ps1`

## Reading the book

| Key | Action |
|---|---|
| `←` / `→` | Turn the page (previous / next by date) |
| `[` / `]` | Previous / next story **in the same chapter** |
| `C` or `Esc` | Back to the table of contents |
| `/` or `Ctrl+K` | Search the whole book |
| Click a photo | Open it full screen (click again to close) |

Your place is bookmarked automatically — the cover shows a **Resume** button.

## If the app looks wrong or outdated

- Refresh once (`F5`) — an old cached page may linger after a rebuild.
- If you changed frontend code, rebuild it: `cd app; npm run build`
- Restart `scrapbook serve` after changing Python code.

## Backing up

Everything lives in `data/` (SQLite database + photos). Copy that folder, or make a
portable bundle:

```powershell
scrapbook export --format bundle
```

## More detail

- [SETUP.md](SETUP.md) — full CLI reference, dev-mode (hot reload), troubleshooting
- [ARCHITECTURE.md](ARCHITECTURE.md) — how the system is designed

### Repo layout

```
app/       React frontend (the book UI) — build output in app/dist
core/      Python: CLI, WordPress connector, FastAPI server, SQLite models
scripts/   assign_topics.py (chapter curation), monthly_update.ps1
config/    source + tag configuration
data/      YOUR ARCHIVE (not in git): database, photos, raw snapshots
```
