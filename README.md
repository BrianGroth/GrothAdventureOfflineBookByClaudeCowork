# Groth Adventures — The Offline Book

A local-first archive of [grothadventures.com](https://grothadventures.com) presented as a
**page-flip book**: a leather cover opens onto two-page spreads — one spread per blog
post — with polaroid photos on the left page and the story on the right. Everything
(posts, photos, search) is stored on your own PC and works completely offline once synced.

The full archive is **999 posts and 3,077 photos spanning 2013–2026** — one page per post.

The book has two tables of contents:

- **By Chapter** — twelve topics: The Bay Area Years 🌉, Life in the Lowlands 🌷,
  Through the Seasons 🍂, Piper & Friends 🐾, Art & Curiosities 🎨,
  Planes, Trains & Bicycles 🚲, European Escapes 🏰, Adventures in Japan 🗾,
  Farther Afield 🦘, American Adventures 🗽, Sunshine Getaways 🏝️,
  Celebrations & Milestones 🎉
- **By Date** — chronological, grouped by year and month, with page numbers

---

## Quick start (first time on a new machine)

> **Shortcut:** after Step 0 below (getting the folder plus Python and Node.js
> installed), you can skip the rest of this section — just double-click
> **`InitialRun.cmd`**. It runs every step for you and finishes with a ready
> book folder. Later, double-click **`Update.cmd`** to pull in new blog posts.
> The steps are still written out below so you know what's happening.

> **Already set up?** If this folder is already on your PC and you've done these steps
> before (e.g. the machine you originally built it on), skip straight to
> [Everyday use](#everyday-use).

### Step 0 — Get this project onto your PC

All the commands below are run from **inside the project folder**, so first you need
the folder itself. Two ways to get it:

- **Git** (recommended, makes updating easy):
  ```powershell
  git clone https://github.com/BrianGroth/GrothAdventureOfflineBookByClaudeCowork.git
  cd GrothAdventureOfflineBookByClaudeCowork
  ```
- **No git:** on the GitHub page click the green **Code** button → **Download ZIP**,
  unzip it somewhere (e.g. `Documents`), and open the unzipped folder.

Then open a **PowerShell window in that folder**: in File Explorer, open the folder,
click in the address bar, type `powershell`, and press Enter. (Or open PowerShell and
`cd` to the folder's path.) Every command below assumes you're sitting in this folder.

You also need two free tools installed (each is a normal Windows installer):

- **Python 3.12+** — [python.org/downloads](https://www.python.org/downloads/)
  (tick "Add python.exe to PATH" during install)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)

### Step 1 — Install the `scrapbook` command

```powershell
pip install -e .
```

The `.` at the end means "install from the *current folder*" — that's why you must run
it inside the project folder. It reads `pyproject.toml` here and installs the project's
Python code plus its dependencies, which gives you a new terminal command: `scrapbook`.
You only ever do this once per machine.

### Step 2 — Create the data folders

```powershell
scrapbook init
```

Don't worry — there is **no database server to install or run**. The "database" is just
one ordinary file (`data\db\scrapbook.sqlite`, a SQLite file) that this command creates,
along with empty folders for photos. Nothing runs in the background; it's all just files
inside this project folder:

```
data\
├── db\scrapbook.sqlite   ← the "database" (a single file)
├── media\                ← photos will be downloaded here
└── raw\                  ← saved copies of the original blog pages
```

### Step 3 — Download the blog (needs internet, one time)

```powershell
scrapbook sync --source grothadventures
```

Pulls every post and photo from grothadventures.com into `data\`. Takes a few minutes.

### Step 4 — Assign posts to book chapters

```powershell
python scripts/assign_topics.py
```

### Step 5 — Build the web app

```powershell
cd app
npm install
npm run build
cd ..
```

### Step 6 — Open the book

```powershell
scrapbook serve
```

This starts a small local server at **http://127.0.0.1:8420** and opens it in your
browser. It's only visible on your own PC. From here on, no internet is needed to read
the book — steps 1–5 never need repeating (except syncing new posts, below).

## Everyday use

Just run (or double-click `run.cmd`):

```powershell
scrapbook serve
```

## Getting new blog posts into the book

Every month or so, with internet: **double-click `Update.cmd`**. It pulls new posts,
re-applies chapters, and refreshes the shareable book folder in one go. (To refresh a
copy on a USB stick directly, run it with the folder as an argument:
`.\Update.cmd E:\GrothBook`.)

Or do the same by hand:

```powershell
scrapbook sync --source grothadventures      # pull new posts + photos
python scripts/assign_topics.py              # re-apply chapters
```

Sync is **incremental by default**: it compares the blog's post list against what's
already in your local database and only downloads posts it doesn't have yet. The
export is incremental too — photos already in the book folder are skipped, so a
refresh takes seconds rather than the ~1 hour a first build needs.

> **Note on old posts.** WordPress.com's sitemap only lists about 1,000 URLs, so a
> normal sync can't see anything older than that cut-off. To reach the full history
> the sync also has to walk the site's month-by-month archives:
>
> ```powershell
> scrapbook sync --source grothadventures --deep
> ```
>
> This has already been run once to pull in everything back to December 2004, so
> you shouldn't need it again — the ordinary `Update.cmd` finds new posts fine.
> It's here in case the archive is ever rebuilt from scratch.

New posts are filed into chapters automatically by keyword. To overrule a choice,
open [scripts/assign_topics.py](scripts/assign_topics.py) and add the post's
permalink slug to `CURATED` (e.g. `"a-day-in-porto": "topic-europe",`), then run
it again. If a post has too little text to classify — a photo with no caption —
the script lists it, ready to paste into `CURATED`, and parks it in a
"New Adventures" chapter meanwhile so the book always works.

There is also a one-shot script that does sync + reindex + export:
`.\scripts\monthly_update.ps1`

## Make a shareable USB / archive copy

To give the book to a friend (or keep a copy that will still open decades from now):
**double-click `InitialRun.cmd`** (builds everything, ends with the book folder at
`data\exports\static-book`), or export directly to a drive:

```powershell
scrapbook export --format static-book --output E:\GrothBook
```

That writes a **plain folder** — the app as one `index.html`, all the photos, and the
stories as data files. Whoever gets the folder needs **no installs and no internet**:
they just double-click **`index.html`** and start flipping pages. Everything works —
both tables of contents, page turns, chapter threads, search, the bookmark.

Updating the copy after you've synced new posts is fast — re-run the same command
into the same folder. Photos are named by their content, so **only new photos get
copied** (existing ones are skipped) and the small data files are refreshed. You do
**not** need to rebuild the app (`npm run build`) unless the UI code itself changed.

Without `--output` it writes to `data\exports\static-book`. Copy the folder to a USB
stick with File Explorer, or export straight to the stick's drive letter as above.

**Size:** the full book folder is about **5.7 GB** (999 stories, 3,077 photos), so use
a 8 GB or larger stick. A first export takes several minutes; refreshing an existing
copy takes under 10 seconds.

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
