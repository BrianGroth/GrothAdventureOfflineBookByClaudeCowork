# Groth Adventures Offline Scrapbook — Product Requirements Document

**Status:** v1 **built and in daily use** (July 24, 2026). Original spec below is
retained as written; §0 records what actually shipped and where the spec was
wrong.
**Date:** June 20, 2026 · **As-built addendum:** July 24, 2026
**Author:** Product/Architecture (Claude, on behalf of Brian Groth)
**Source documents:** `ARCHITECTURE.md` (stack decisions, final — not relitigated here); live reconnaissance of `grothadventures.com` performed June 20, 2026 (see citations inline)

---

## 0. As-Built Addendum (July 24, 2026)

**Read this before trusting the sections below.** §§1–11 are the original
pre-build specification. The product was built, then substantially redesigned
during use. Where this section and a later section disagree, this one is correct.

### 0.1 What changed most: it became a book, not a website

The spec described a scrapbook *website* (Home, Timeline, Entry page, Search
page — §6, §7). That was built and then replaced, because browsing it felt like
scrolling a blog rather than turning pages. The shipped product is a **book**:

- A closed leather **cover** opens the archive.
- Each post is one **two-page spread** — photos as tilted polaroids on the
  verso, story with a drop cap on the recto, plus running heads and folios.
- **Two tables of contents**: *By Chapter* (12 curated topics) and *By Date*
  (year → month), both listing page numbers with dotted leaders.
- **Two navigation axes**: `←`/`→` turn pages chronologically; `[`/`]` follow
  the current chapter's thread across years. `C`/`Esc` return to contents.
- A **bookmark** is saved automatically; the cover offers "Resume".
- Page turns animate as a 3D sheet fold, disabled under
  `prefers-reduced-motion`.

Curate mode (§8) and map view were **not** built. Chapter assignment happens in
`scripts/assign_topics.py`, not in the UI.

### 0.2 New capability not in the spec: the standalone book folder

§9 anticipated a "static fallback" as a stretch goal. It shipped as a
first-class feature and is now the primary way the archive is shared:

```
scrapbook export --format static-book --output E:\GrothBook
```

This writes a folder that opens by **double-clicking `index.html`** — no server,
no Python, no internet, nothing installed. Full functionality: both TOCs, page
turns, chapter threads, search, lightbox, bookmark.

Making one build work both served and from `file://` forced three decisions:
**single-file build** (all JS/CSS/fonts inlined, since `file://` blocks module
scripts), **hash routing** (`#/page/5`, since there is no server to rewrite
URLs), and **data as classic scripts** rather than `fetch()` (which `file://`
blocks) — `boot.js` for the TOC, one file per entry, plus a text index for
in-browser search.

Measured: 999 stories + 3,077 photos = **5.7 GB**; first export several minutes,
subsequent refreshes **~9 seconds** (photos are content-addressed, so only new
ones copy).

### 0.3 Corrections to §2.7 — the archive is smaller *and* incomplete

The spec estimated **~1,700 posts spanning December 2004 – May 2026**. Measured
against the live site on July 24, 2026:

| Claim in spec | Measured reality |
|---|---|
| ~1,700 posts, from Dec 2004 | **999 posts ingested, from Aug 24 2013** |
| Sitemap enumerates the archive | Sitemap is one flat file of **2,329 URLs**, only **999 of which are posts** (rest are `wp-content/uploads` media) |
| — | WordPress.com appears to **cap the sitemap at ~1,000 URLs**, silently hiding everything older |

**All 999 sitemap-listed posts are archived locally — verified zero missing.**

However, **older posts still exist and are not ingested.** Year archives
`/2004/`, `/2008/`, `/2011/`, `/2012/` all return real posts.

This is an **implementation deviation from this PRD, not a spec gap**. Task 1.1
(§10) required "Stage 0 discovery: robots.txt parse, sitemap.xml parse,
**archive-index walk (back to 2004/12)**" and set the acceptance bar at "within a
few percent of the ~1,698 reference figure". As built,
`WordPressConnector._discover_posts()` calls `_walk_archives()` **only if the
sitemap yields zero URLs** — so against a populated-but-truncated sitemap the
archive walk never runs, and the acceptance criterion (999 ≉ 1,698) was never
enforced.

**Fix:** always walk year/month archives and union the results with the sitemap,
deduplicating on canonical permalink.

**Measured gap (read-only crawl of monthly archives, 2026-07-24):**

| Year | Missing posts | | Year | Missing posts |
|---|---|---|---|---|
| 2004 | 7 (blog starts 2004-12-02) | | 2009 | 69 |
| 2005 | 34 | | 2010 | 44 |
| 2006 | 102 | | 2011 | 114 |
| 2007 | 132 | | 2012 | 61 |
| 2008 | 95 | | 2013 (to Aug 21) | 41 |

**699 posts missing**, earliest `2004/12/02/brian-and-lories-children-the-bunny-and-the-dog`,
latest `2013/08/21/sitting-on-top-of-the-world`.

**999 ingested + 699 missing = 1,698 — exactly the "~1,698 reference figure"
this PRD derived from the site's archive widget in §2.7.** The original
reconnaissance was correct; the connector simply never looked past the sitemap.
Note 699 is a *floor*: the crawl capped at 6 pages per month.

**This is the single largest open gap in v1** — the difference between "the
whole blog" and "the blog since August 2013". Roughly 41% of the archive, and
the entire pre-Amsterdam era, is absent.

### 0.4 Chapters (topics) — how they actually work

The spec's tagging plan (§2 "Tagging", §3 `Tag`) produced weak results: keyword
auto-tags mislabelled posts (e.g. a New York trip tagged *Skiing*). Chapters are
therefore a separate, curated layer stored as `Tag(category='collection')` rows
with slugs `topic-*`, applied in two passes by `scripts/assign_topics.py`:

1. **Curated** — a hand-built map of *permalink slug → chapter* (`auto=0`).
   Keyed by slug, not database id, so a rebuild on another machine reproduces
   the same book.
2. **Keyword scoring** — for everything else: whole-word matches, title worth 3×
   body, ordered rules where a recurring series beats its location. Anything
   with no signal lands in a visible "New Adventures" holding chapter and is
   printed for hand-filing.

The 12 chapters: The Bay Area Years, Life in the Lowlands, Through the Seasons,
Piper & Friends, Art & Curiosities, Planes/Trains & Bicycles, European Escapes,
Adventures in Japan, Farther Afield, American Adventures, Sunshine Getaways,
Celebrations & Milestones.

### 0.5 Operations — two double-clickable scripts

Replacing the CLI-first routine in §4 for everyday use:

- **`InitialRun.cmd`** — first build on a new machine: install deps → init DB →
  sync → chapters → build frontend → export the book folder. Skips finished steps.
- **`Update.cmd`** — monthly: new posts → re-file chapters → refresh book folder.

Both accept an optional destination folder and pin themselves to their own
copy of the project (`SCRAPBOOK_DATA_DIR` + `python -m core.cli`). That pinning
exists because `pip install -e .` binds the `scrapbook` command to whichever
clone installed it — with two clones on one machine, steps silently operated on
different archives.

### 0.6 Bugs found and fixed during the full-archive ingest

- **Sync aborted on duplicate photos** — a post reusing one image twice violated
  `entry_media`'s unique constraint (the session runs `autoflush=False`, so the
  guard query could not see the pending row). Now de-duplicates per post, and a
  single bad post rolls back and is skipped instead of killing an hours-long run.
- **Dead Windows Live Writer embeds** — 23 posts (2013–2015) rendered their
  title twice followed by "VIEW SLIDE SHOW / DOWNLOAD ALL" links to defunct
  SkyDrive albums. Prose cleanup now parses the DOM instead of using regexes.
- **Drop cap never rendered** — posts arrive wrapped in `<div class="content">`,
  so no `<p>` was a direct child of the prose container.
- **Stale `index.html`** — served without cache headers, so rebuilds appeared
  not to take effect. Now `Cache-Control: no-cache`.

### 0.7 Current state

| Metric | Value |
|---|---|
| Posts (pages in the book) | 999 |
| Photos | 3,077 |
| Date range | Aug 24 2013 – May 27 2026 |
| **Blog coverage** | **~59% (999 of ~1,698) — see §0.3** |
| Local archive (`data/`, gitignored) | ~11.5 GB |
| Exported book folder | ~5.7 GB |
| Chapters | 12 |
| Sync / export correctness | 999/999 sitemap posts present; `errors: 0` |

---

## 1. Executive Summary

**What this is.** The Groth Adventures Offline Scrapbook is a local-first desktop application that periodically pulls every post and photo from `grothadventures.com` — Brian and Lorie Groth's travel/life blog, running continuously since December 2004 — into a durable local archive on Brian's own PC, and presents it as a beautiful, browsable, fully offline scrapbook. It is not a hosted product and has no server-side component beyond `localhost`. Once synced, the entire 20+ year archive (text, photos, dates, places) is available with zero network dependency.

**Who it's for.** A single user (Brian, with Lorie as a secondary viewer) who wants: (1) a permanent, ownable backup of two decades of personal history that does not depend on WordPress.com's continued existence, (2) a much nicer way to browse that history than a paginated blog theme, and (3) a light curation workflow to clean up tags, covers, and organization a few times a year.

**Why it matters.** `grothadventures.com` is a hosted WordPress.com blog (confirmed via `robots.txt` and page metadata — `meta-generator: WordPress.com`, footer "Blog at WordPress.com"). It is not self-hosted, not exported automatically, and not under Brian's infrastructure control. The blog contains roughly **1,700 posts** spanning **December 2004 to May 2026** (computed from the site's own archive widget — see §2.7) with potentially **tens of thousands of photos**, some now only existing as web-resized derivatives on WordPress.com's CDN. Today, there is no local, durable, full-resolution copy of this content and no way to browse it except through the live, paginated, ad-adjacent WordPress.com theme. This project converts a rented, single-point-of-failure asset into an owned, preservable, beautifully presented one.

**What "done" looks like (v1).**

- Running `scrapbook sync --source grothadventures` performs a complete or incremental crawl of the site and populates a local SQLite database plus a content-addressed media store with every reachable post and image, without creating duplicates on rerun.
- A local web app (FastAPI + React, served at `http://localhost:8420`) lets Brian browse a Table of Contents by year, a chronological Timeline with cover photos, individual Entry pages with full text and photo galleries, and full-text Search — all rendered in a parchment/polaroid scrapbook visual style — with **zero network calls** required after sync.
- A Curate mode lets Brian fix titles, dates, tags, covers, and photo order, and a Review Queue surfaces newly-synced entries that need attention.
- `scrapbook export --format bundle` produces a self-contained, checksummed "vault bundle" directory that can be copied to an external drive or cloud backup and still browsed (at minimum via the local app pointed at that bundle; ideally via a static fallback — see §9).
- The whole loop (`sync` → `review` → `export` → backup) is the "every few months" operating routine described in `ARCHITECTURE.md`, runnable by one person with no DevOps.

**What's explicitly out of scope for v1:** map view (stubbed for v2), additional connectors (photo libraries, scanned albums — Phase 4), multi-user accounts, cloud sync/hosting, and comment ingestion (see §11 for the decision needed on whether to ever ingest WordPress comments).

---

## 2. Ingestion Specification (grothadventures.com connector)

### 2.1 Site facts established by reconnaissance (June 20, 2026)

These are not assumptions — each was confirmed by fetching the live site:

| Fact | Evidence |
|---|---|
| Hosting platform | WordPress.com (mapped custom domain), **not** self-hosted WordPress | `meta-generator: WordPress.com`; footer "Blog at WordPress.com."; underlying site appears to be `grothadventures.wordpress.com` (seen in `og:image:secure_url` → `https://i0.wp.com/grothadventures.wordpress.com/wp-content/uploads/...`) |
| Permalink structure | `https://grothadventures.com/{YYYY}/{MM}/{DD}/{slug}/` | Observed on every post, e.g. `/2026/05/27/our-cows-horses/` |
| Sitemaps | `https://grothadventures.com/sitemap.xml` and `https://grothadventures.com/news-sitemap.xml` | Declared in `robots.txt` |
| Sitemap format | Flat `<urlset>` of `<url><loc>/<lastmod>/<changefreq>` entries, with optional `<image:image>` children listing in-post image URLs | Fetched and parsed directly; confirmed **not** a sitemap-index-of-sitemaps |
| Sitemap completeness | A single fetch returned ~143 `<url>` entries and ~340 `<image:loc>` entries before being truncated by tooling, well short of the full ~1,700-post archive | Direct fetch; the connector **must not** assume `sitemap.xml` alone is a complete backfill source — treat it as a fast "what's new" feed, not the system of record (see §2.3) |
| `news-sitemap.xml` | Per Google News sitemap convention, contains only posts from roughly the last 48 hours | Standard WordPress.com behavior; not useful for backfill, only as a secondary "anything just published" check |
| `robots.txt` politeness rules | See §2.4 verbatim below | Fetched directly |
| Self-hosted REST API (`/wp-json/wp/v2/posts`) | Returned HTTP 200 but an empty/non-rendering body when probed in this session | **Unverified — flagged as an Open Question (§11)**. Many WordPress.com-hosted (non-Business-plan) sites disable or restrict `wp/v2` write/list endpoints. Do not build the connector assuming this works; verify with a raw HTTP client (not a markdown-extracting fetcher) before relying on it. |
| WordPress.com public API (`public-api.wordpress.com/rest/v1.1/sites/grothadventures.com/posts/`) | Same empty-body result when probed | **Unverified — same flag.** This is normally the more reliable JSON path for WordPress.com-hosted sites (works without auth for public blogs) and should be the **first thing the engineer verifies** with `curl`, since if it works it is strictly better than HTML scraping (structured JSON: `ID`, `date`, `modified`, `title`, `content`, `excerpt`, `slug`, `categories`, `tags`, `featured_image`, `author`). |
| HTML index pages render full content | Confirmed: the homepage and (by inspection of theme behavior) monthly archive pages render the **complete post body HTML**, not excerpts, for ~10 posts per page, paginated via `/page/N/` | Direct fetch of `https://grothadventures.com/` returned full multi-paragraph bodies and all `<img>` tags for 10 consecutive posts |
| Per-post page metadata | Canonical URL, `og:title`, `og:description`, `og:image` (full-resolution), `twitter:image`, `article:published_time` / `article:modified_time` (ISO-8601 UTC), category breadcrumb, WP.com shortlink (`https://wp.me/...`), comment count | Direct fetch of a permalink page |
| Categories/tags usage | Most sampled posts fall under a single generic `Uncategorized` category; no visible per-post tag list in rendered HTML | Direct fetch — **confirms** `ARCHITECTURE.md`'s assumption that auto-tagging must rely on heuristics (title/body keywords, date) plus manual curation, not source taxonomy |
| Image hosting | Images live at `grothadventures.com/wp-content/uploads/{YYYY}/{MM}/{filename}`, frequently requested with a Jetpack/Photon resize query string (`?w=1024`); the canonical original is reachable by stripping the query string | Multiple `<img src>` values observed, e.g. `.../2026/05/img_8427.jpg?w=1024`; `og:image` for the same post showed the unscaled `width=2000/height=1500` original at the same path with no `?w=` |
| Filename patterns | Two distinct patterns: camera-native (`img_8423.jpg`, lowercase) and random UUID (`e7c2edb1-8f31-4dcb-a722-785d08dfc4ef.png`) | Observed across multiple posts; UUID-named files are typically phone-share-sheet uploads or **AI-edited** versions explicitly called out in post body text (e.g. "The brighter photo is AI's attempt to make one of my photos look less washed out") — both must be ingested as distinct media; do not attempt to dedupe an AI-edited derivative against its source photo (their bytes and hashes legitimately differ) |
| External video | Posts occasionally contain bare YouTube URLs in body text (e.g. `https://youtube.com/shorts/dvZTn_bVHO4`), not embedded `<iframe>`s | Observed in "Malta, March 2026" and "December Dublin" posts |
| Estimated post volume | **~1,698 posts**, Dec 2004 – May 2026 (~21.5 years) | Computed by summing every per-month count shown in the site's own "Archives" sidebar widget (full table retained in connector test fixtures — see §2.7) |

### 2.2 Connector identity & politeness

```yaml
# config/sources.yaml
sources:
  - id: grothadventures
    type: wordpress
    name: "Groth Adventures (grothadventures.com)"
    base_url: "https://grothadventures.com"
    config:
      user_agent: "GrothAdventuresScrapbookBot/1.0 (+personal archive tool; operated by groth.brian@gmail.com; respects robots.txt)"
      request_timeout_sec: 20
      min_delay_sec: 1.5        # politeness floor between any two requests to the site
      max_delay_sec: 3.0        # jittered upper bound (delay = random(min,max))
      max_concurrent_requests: 2
      max_concurrent_media_downloads: 4   # used by Stage 3 media downloads (§2.3)
      media_timeout_sec: 60               # media files are multi-MB; longer than the post-page timeout below
      max_retries: 4
      backoff_base_sec: 2.0     # exponential backoff: base * 2^(attempt-1), capped at 60s
      respect_robots_txt: true
      api_mode: "auto"          # auto | wpcom_api | html   (see §2.3)
```

**Rate-limit model:** `min_delay_sec`/`max_delay_sec` is a **single global rate gate** shared by every request the connector makes to `grothadventures.com`, regardless of which pool (post-fetch or media-download) issued it — implemented as one timestamp-gated token bucket/semaphore that every outbound request awaits before firing, independent of `max_concurrent_requests`/`max_concurrent_media_downloads` (which only cap how many requests may be *in flight* at once, e.g. for connection-pool sizing). Concretely: even with 2 post-fetch workers and 4 media-download workers all active, the connector never sends two requests to the site closer together than `min_delay_sec`, full stop.

`robots.txt` (fetched verbatim, June 20, 2026) imposes no explicit `Crawl-delay`, but does:

```
Sitemap: https://grothadventures.com/sitemap.xml
Sitemap: https://grothadventures.com/news-sitemap.xml
User-agent: *
Disallow: /wp-admin/
Allow: /wp-admin/admin-ajax.php
Disallow: /wp-login.php
Disallow: /wp-signup.php
Disallow: /press-this.php
Disallow: /remote-login.php
Disallow: /activate/
Disallow: /cgi-bin/
Disallow: /mshots/v1/
Disallow: /next/
Disallow: /public.api/
```

The connector MUST: parse and obey this file at the start of every `sync` run (cache it for the run, re-fetch each new run since WordPress.com regenerates it daily), never request a disallowed path, and self-impose `min_delay_sec`/`max_delay_sec` and `max_concurrent_requests` regardless of whether robots.txt specifies a crawl-delay, because this is Brian's own content and there is no reason to hammer WordPress.com's shared infrastructure. The `User-Agent` string identifies the bot and an owner contact, per courtesy convention.

### 2.3 Crawl sequence

The connector runs in four ordered stages every `sync` invocation. Each stage is individually resumable (state persisted in `ingest_runs.stats_json`) so a killed process can restart at the right stage instead of re-crawling from scratch.

**Stage 0 — Discovery (always runs, cheap).**
1. Fetch `/robots.txt`; parse disallow rules using a real RFC 9309-aware parser library (`protego`, the parser Scrapy uses — more correct than Python's stdlib `urllib.robotparser`, which has known wildcard/precedence bugs) rather than custom string matching. This matters because the file mixes `Disallow`/`Allow` at different specificities, e.g. `Disallow: /wp-admin/` + `Allow: /wp-admin/admin-ajax.php`.
2. Fetch `/sitemap.xml`. Parse all `<url>` entries into `(loc, lastmod, image_locs[])` tuples. Because this file has been observed to be large/possibly capped, treat it as a **delta hint**, not ground truth: any URL present here with `lastmod` newer than that URL's locally-stored `Entry.updated_at` is queued as "changed — needs refetch."
3. Fetch `/news-sitemap.xml` defensively (best-effort; 404/empty is not an error) for "published in the last 48h" coverage.
4. **Full mode only** (first run, or `--full` flag): crawl the monthly archive index. Reconnaissance observed single months with far more posts than fit on one archive page (e.g. October 2018 = 36 posts, April 2017/2018 = 34 each, against an observed ~10-posts-per-page rendering limit), so the walk must paginate within each month, not just walk backward month-by-month:
   - a. Fetch any already-known page (the homepage works) and parse its **Archives widget** — confirmed present on every page during reconnaissance, rendered as a literal list of `(label, url, count)`, e.g. `<li><a href="https://grothadventures.com/2026/05/">May 2026</a> (2)</li>`. Parsing this widget (not a hardcoded "2004/12" constant) gives the connector the *exact, current* set of `(year, month) → expected_post_count` to target — this is what actually defines "done" for the archive walk, not an assumption baked into the code.
   - b. For each `(year, month)` in that list, fetch `/{year}/{month}/`, extract every post permalink shown on the page, and **follow pagination**: if the page contains an "Older Entries" link (observed pattern: `/{year}/{month}/page/2/`), follow it and keep accumulating permalinks until no further "Older Entries" link is found.
   - c. After accumulating a month's permalinks, compare the count actually found to the widget's stated count for that month. Mismatch → log a new error class `ARCHIVE_COUNT_MISMATCH` (§2.4) for that month (not a crawl-aborting error — just a flag for the run summary) so silent under-crawling of a month is visible rather than assumed-fine.
5. Union the URL lists from steps 2–4 into a single deduplicated **candidate URL list**, each tagged with the discovery source (`sitemap`, `archive_index`, `news_sitemap`).

**Stage 1 — Post list resolution (per candidate URL).**
For each candidate permalink URL, determine whether it needs a fetch:
- Not yet in `entries` table → fetch (new).
- In `entries` table, but sitemap `lastmod` (or archive-page `lastmod`, when available) is newer than stored `Entry.source_updated_at` → fetch (changed).
- Otherwise → skip (unchanged); still counts toward run stats.

If `api_mode` resolves to `wpcom_api` (see decision rule below), Stage 1 instead pages through `GET https://public-api.wordpress.com/rest/v1.1/sites/grothadventures.com/posts/?number=100&page_handle=...`, where `page_handle` for each request after the first is taken verbatim from the previous response's `meta.next_page` field (standard WP.com API pagination convention) — treating each returned post object as already-fetched (skip Stage 2 entirely for that entry; the API response **is** the canonical record). **Not detailed further than this** — `api_mode=html` is the v1 default and this path is an opportunistic future optimization, not load-bearing for launch.

`api_mode: auto` resolution rule (run once per `sync`, cached for the run): attempt one call to the WP.com public API for a single known post ID; if it returns HTTP 200 with a JSON body containing a `content` field, use `wpcom_api` mode for the whole run; otherwise fall back to `html` mode. This makes the connector self-healing if WordPress.com's API posture changes.

**Stage 2 — Per-post fetch & extraction (HTML mode).**
For each URL needing a fetch:
1. `GET` the permalink with the configured `User-Agent`, honoring rate limits.
2. Save the raw response (HTML bytes + response headers) as an immutable snapshot (§2.5).
3. Extract via CSS/structural selectors against the page DOM:
   - `title` — from `<meta property="og:title">` (HTML-entity-decoded), falling back to `<h1>` inside the article element.
   - `body_html` — the article content container. **Selector strategy:** attempt, in order, the standard WordPress core content-container classes that the `the_content()` template tag has wrapped output in across virtually every theme (including custom WordPress.com themes) for 15+ years: `.entry-content`, `.post-content`, `.post-entry`, `article .entry`. If none of those match (plausible for a 20-year-old archive that has likely been through multiple WordPress.com theme changes — §11.4), fall back to a **structural extraction** that needs no class name at all: take everything inside the page's `<article>`/`<main>` element, starting immediately after the title heading (`<h1>`/`<h2>` matching the extracted `title`) and ending at the first of several known boilerplate anchors observed directly in reconnaissance — the literal text "Share this:", "Like Loading", or "*Related*", or the start of the comment form/"Leave a comment" block. This bounds the content region using stable text landmarks confirmed present on every sampled post page, rather than a guessable CSS class, so the extractor degrades gracefully across theme eras instead of failing outright.
   - `event_date` — `entry.event_date`/`entry.source_event_date` are **date-only** strings (`YYYY-MM-DD`, no time component — this is now explicit in §3.1 and the DDL comments), and the **authoritative source is always the permalink path's `/YYYY/MM/DD/` segments**, not the `article:published_time` meta tag. This is a deliberate design choice, not just a fallback: WordPress generates the permalink date from the post's own locally-configured date at save time, while `article:published_time` is rendered in UTC — converting UTC back to "the date Brian actually experienced" risks an off-by-one-day error for any post made late at night in his local timezone. The permalink path has no such ambiguity and is present on 100% of posts. `article:published_time`/`article:modified_time` are still extracted, but only feed `source_updated_at` (§2.6 change-detection, where sub-day time precision is actually useful) — never `event_date`.
   - `source_updated_at` — `<meta property="article:modified_time">`, stored as a full ISO-8601 UTC datetime (`YYYY-MM-DDTHH:MM:SSZ`) — unlike `event_date`, this field's precision matters for resync diffing (§2.6).
   - `category breadcrumb` → seed tag of `type=topic`, **except** when the breadcrumb category is literally `"Uncategorized"` (WordPress's default category name for any post where the author never picked one — recon showed nearly every sampled post falls under this exact default). Seeding a `topic:Uncategorized` tag on ~95% of entries would create a useless, universal tag that adds review-queue/UI noise without conveying any information — so this specific literal value is excluded from auto-tagging (case-insensitive comparison), while any other category name is still seeded normally.
   - `image URLs` — every `<img src>` inside the content container, plus the `og:image` (as the candidate cover/featured image, recorded as `position=0, is_cover=true` if no img already occupies position 0). **`srcset`/`sizes` attributes are ignored entirely** — not needed, since stripping the Photon `?w=` query string from any single resolution found in `src`, per the rule below, already yields the full original file regardless of which responsive breakpoint happened to be in `src`. **Exact-duplicate URLs within the same post** (e.g. a theme accidentally rendering one image twice) are de-duplicated at extraction time: only the first occurrence becomes an `EntryMedia` row; later occurrences of the identical normalized URL in the same post are dropped rather than creating a second link row at a later position.
   - `external video references` — regex-scan **both the raw `body_html` markup and its stripped text** for `(youtube\.com|youtu\.be)/\S+` and `(vimeo\.com)/\S+`. WordPress's core `make_clickable()` filter, part of the standard `the_content` filter chain on virtually every WordPress install including WordPress.com, auto-converts bare URLs into `<a href="{url}">{url}</a>` links before saving/rendering — so the parser must handle **both** cases —
     - If the URL is already inside an `<a href="{url}">...</a>` tag (link text equal to the URL itself, or any text), replace the **entire anchor element** with `<a class="video-ref" href="{url}" data-provider="youtube|vimeo">▶ Watch on {provider}</a>`.
     - If the URL appears as bare, unlinked text, wrap just the matched URL substring the same way, in place.
     Either way, store a `Media` row with `mime_type='external/video'`, `status='external_reference'`, and `storage_path=NULL` (no download — see §3.3 Media table, §5.5 for how these serve via the API). The Entry page's sanitizer allowlist (§6.3) already permits `<a>` tags, so no allowlist change is needed.
   - `source_entry_id` — exact canonicalization algorithm:
     ```python
     from urllib.parse import urlparse
     import hashlib

     def source_entry_id(permalink_url: str) -> str:
         path = urlparse(permalink_url).path.strip("/").lower()
         # e.g. "https://grothadventures.com/2026/05/27/our-cows-horses/" -> "2026/05/27/our-cows-horses"
         return hashlib.sha256(path.encode("utf-8")).hexdigest()
     ```
     WordPress.com does not expose a numeric post ID in public HTML (the only ID-like value visible, the `wp.me` shortlink suffix, is a base36 hash of the real ID and is not guaranteed stable enough to parse as a primary key — store it anyway as `Entry.shortlink` for reference, but do not use it as the dedup key).
4. Normalize `body_html` → `body_text` (HTML-stripped, whitespace-collapsed) for FTS indexing.
5. Hand the extracted image URL list to Stage 3.

**Stage 2 — Per-post fetch & extraction (API mode, when verified working).**
Map WP.com REST fields directly: `ID → source_entry_id`, `title.rendered or title → title`, `content.rendered or content → body_html`, `date_gmt → event_date`, `modified_gmt → source_updated_at`, `slug → canonical_slug`, `categories[]`/`tags[]` → seed `Tag` rows, `featured_image` → cover `Media` candidate. Raw JSON response is the snapshot (§2.5) instead of raw HTML.

**Stage 3 — Media download.**
For every image URL gathered in Stage 2:
1. Normalize to the **original-resolution** form: strip any `?w=`, `?h=`, `?resize=`, `?ssl=` query parameters (these are Jetpack Photon/Site Accelerator resize directives layered on top of the real file at that path — confirmed by comparing a `?w=1024` thumbnail URL and its corresponding `og:image` full-resolution URL at the *same path with no query string*).
2. `GET` the normalized URL with the same rate limiting as post fetches but a separate concurrency pool (`max_concurrent_media_downloads: 4` — media downloads are larger and less CPU-bound on the WordPress.com side, but still must respect `min_delay_sec`).
3. On success: compute `sha256` over the downloaded bytes, look up `Media` by hash.
   - If a `Media` row with that hash already exists (from this or any other post — e.g., the same photo reused in two posts), reuse it; only insert a new `EntryMedia` link row.
   - If not, insert a new `Media` row, write the bytes to the content-addressed store (§3.5), and extract `width`/`height` (via Pillow) and `exif_json` (via `exifread`/Pillow `getexif()`), and `mime_type` (via `python-magic` or Pillow format, not the HTTP `Content-Type` header alone — WordPress.com sometimes serves images with imprecise content types).
4. On failure: classify per §2.6 error taxonomy; record on `IngestRun.stats_json` and continue (one bad image must never abort the run).
5. After all media for an entry resolve, rewrite `Entry.body_html`'s `<img src>` values to local-relative references (`media://{sha256}`, resolved by the frontend/API to the actual served path — see §5.5) so the offline app never needs network access to render a post. Concrete before/after for the "Our Cows & Horses" post (real reconnaissance data):
   ```html
   <!-- As fetched from the source (Stage 2 raw extraction) -->
   <img src="https://grothadventures.com/wp-content/uploads/2026/05/img_8423.jpg?w=1024">

   <!-- After Stage 3 rewriting, as stored in entry.body_html -->
   <img src="media://3f9ad8c2e1b7a4f0...d92e" data-width="2000" data-height="1500" alt="">
   ```
   `width`/`height` attributes are populated from the now-known `Media.width`/`Media.height` (so the frontend can reserve layout space before the image loads, avoiding content jank); `alt` is carried through from the source `<img alt>` if present, else left empty (the frontend's own `alt` fallback, §7.6, fills it in at render time — `body_html` itself is allowed to have an empty `alt` since it's not the final rendered output). The `media://{sha256}` scheme is a storage-layer placeholder, not a real URL — the API layer (§5.2 `GET /api/entries/{id}`) resolves it to the actual `/api/media/{sha256}/full` path before the JSON response is sent to the frontend, so the frontend never sees or parses `media://` itself.

**Stage 4 — Upsert.**
1. Upsert the `Entry` row (insert if new; update if `source_updated_at` advanced — see §2.6 conflict rules).
2. Upsert `EntryMedia` link rows (position, caption from adjacent `<figcaption>`/alt text if present, `is_cover`).
3. Apply auto-tagging heuristics (date-based tags always; keyword-dictionary topic tags — see §2.8) as `EntryTag` rows with `source='auto'`, never overwriting any existing tag with `source='manual'`.
4. Mark the entry `review_status='pending'` if it is brand new, so it surfaces in the Curate Review Queue (§8).
5. Update `IngestRun.stats_json` counters: `posts_seen`, `posts_new`, `posts_updated`, `posts_unchanged`, `posts_error`, `media_downloaded`, `media_deduped`, `media_error`, `bytes_downloaded`.

### 2.4 Retry & error handling taxonomy

| Class | Trigger | Action |
|---|---|---|
| `HTTP_429_RATE_LIMITED` | HTTP 429, or 503 with `Retry-After` | Honor `Retry-After` header if present; else exponential backoff (`backoff_base_sec * 2^attempt`, capped 60s); retry up to `max_retries`; if exhausted, mark item `error`, continue run |
| `HTTP_404_NOT_FOUND` (post) | Permalink in candidate list returns 404 | Mark entry `status='removed_at_source'` (do **not** delete local copy — preservation principle); log to run stats; do not retry |
| `HTTP_404_NOT_FOUND` (media) | Image URL 404s | Record `Media` placeholder row with `status='missing_at_source'`, `storage_path=NULL`; surfaced in Curate Review Queue as "broken image — relink or remove"; do not retry within the same run |
| `HTTP_5XX` | Server error | Exponential backoff retry up to `max_retries`; if exhausted, mark `error`, continue |
| `TIMEOUT` | No response within `request_timeout_sec` | Treated as transient; same backoff/retry as 5xx |
| `MALFORMED_HTML` | Expected content container selector not found | Save the raw snapshot anyway (preservation always happens before parsing); mark entry `status='parse_error'`; surface in Review Queue with the raw snapshot path so a human (or a future improved parser + `scrapbook reindex`) can resolve it later; do not silently drop the post |
| `CHECKSUM_MISMATCH` | Downloaded byte count doesn't match `Content-Length` header (when present) | Discard partial download, retry once immediately, then fall back to standard backoff/retry |
| `INVALID_IMAGE_DATA` | Covers a download that completes successfully, with no `Content-Length` mismatch, but isn't actually a valid image — e.g. chunked-encoding responses where there's no length to check against, or a CDN error page served with HTTP 200; detected because Pillow's `Image.open(...).verify()` raises on the downloaded bytes | Treat like `HTTP_404_NOT_FOUND` (media): record `Media` row with `status='missing_at_source'`, surface in Review Queue identically — from the user's perspective "downloaded garbage" and "never downloaded" need the same fix (relink or remove), so they share a status rather than needing a new one |
| `ARCHIVE_COUNT_MISMATCH` (§2.3 Stage 0 step 4c) | A month's accumulated permalink count (after following all "Older Entries" pagination) doesn't match the Archives widget's stated count for that month | Not a per-item error — logged once per affected month on `IngestRun.stats_json` (`archive_mismatches: [{"month": "2018-10", "expected": 36, "found": 34}]`); does not abort or retry, just flags the month as possibly under-crawled for human follow-up |
| `DNS_OR_CONN_ERROR` | Network-level failure | Same backoff/retry. One shared counter across both post-fetch and media-download failures (they share the same underlying connectivity to the same host), incremented on any `DNS_OR_CONN_ERROR` or a `TIMEOUT` that has exhausted its own retries, and reset to zero on any single successful fetch of either kind. When the counter reaches 3, **abort the run early** (likely a connectivity or block issue, not a per-item issue) and report clearly rather than retrying 1,700 times |

All errors are additive to `IngestRun.stats_json` and never raise past the per-item boundary except the early-abort case above. `scrapbook sync` always exits 0 if the run completed (even with some per-item errors) and prints an error summary; it exits non-zero only on early abort or a configuration/auth failure (see §4 exit codes).

### 2.5 Raw snapshot format & storage path conventions

Every successful Stage 2 fetch (HTML or API mode) is persisted **before** parsing, verbatim, so the system of record can always be reprocessed if the parser improves.

```text
data/raw/grothadventures/
  {YYYY}/{MM}/{DD}-{slug}/
    response.html            # HTML mode: raw bytes as received
    response.json            # API mode: raw JSON as received (mutually exclusive w/ .html)
    headers.json             # {"status": 200, "content-type": "...", "etag": "...", "fetched_at": "2026-06-20T14:03:11Z", "url": "..."}
```

Example: a fetch of `https://grothadventures.com/2026/05/27/our-cows-horses/` on 2026-06-20 is stored at
`data/raw/grothadventures/2026/05/27-our-cows-horses/response.html` with a sibling `headers.json`.

If the same `(source_id, source_entry_id)` is refetched later because `source_updated_at` advanced, the **previous** snapshot directory is renamed with a `.v{N}` suffix (`27-our-cows-horses.v1/`) rather than overwritten — raw snapshots are immutable and cumulative, per the "source preservation" product principle in `ARCHITECTURE.md`. The current snapshot is always the highest-numbered (or un-suffixed = latest) directory; `Entry.raw_snapshot_path` always points at the current one.

**Retention policy:** versioned snapshots accumulate forever in v1, with no automatic pruning. This is intentional: the product principle is explicit source preservation, post edits on a personal blog are realistically rare (most of this archive is decade-old and static), and the storage cost of an extra HTML snapshot (tens of KB) is negligible next to the media store (tens of GB) — so there's no meaningful storage pressure to optimize away. If this assumption ever proves wrong in practice, pruning old `.vN` directories is a future `scrapbook` flag, not a v1 requirement.

### 2.6 Idempotency & conflict resolution

**Primary dedup key:** `(source_id, source_entry_id)`, unique-constrained in the DB (§3). `source_entry_id` is computed as:
- API mode: the WordPress.com numeric post `ID`, stringified.
- HTML mode: `sha256(canonical_path)` where `canonical_path` is the permalink path lower-cased, with any trailing slash normalized to present, and any tracking query string stripped (e.g. `2026/05/27/our-cows-horses`). This is stable across protocol/host changes and across `?utm_source` noise, and stable even if the WP.com API later becomes available (a one-time backfill migration would map HTML-derived IDs to API IDs once confirmed equivalent — see §11).

**Fallback key.** The realistic v1 trigger for this path is a post's URL/slug changing at the source (e.g. WordPress.com renaming a slug), which mints a brand-new `source_entry_id` hash for what's actually the same underlying post. Fallback match rule: normalized-URL match OR (`title` fuzzy match ≥ 0.92 Jaro-Winkler AND `event_date` exact match), computed via `rapidfuzz.distance.JaroWinkler.normalized_similarity`. When the fallback key fires a probable duplicate, the entry is **not** auto-merged; it is flagged `review_status='possible_duplicate'` with a pointer to the other entry's ID, surfaced in the Curate Review Queue for a human merge/dismiss decision. Auto-merging two entries is never done silently.

**Media dedup key:** `Media.sha256` (full file content hash), unique-constrained. Identical bytes anywhere on the site (same photo reused in two posts, or refetched unchanged) always collapse to one `Media` row with multiple `EntryMedia` links. AI-edited derivatives and resized variants have different bytes and therefore correctly remain distinct rows (no perceptual/fuzzy image hashing in v1 — see §11 for whether that's wanted later).

**Conflict resolution on resync (source changed):**
1. If `source_updated_at` from the source is newer than the stored value → this is an **update**, not a conflict: the new raw snapshot is saved (versioned per §2.5), `Entry.body_html`/`body_text`/`title`/`event_date` are overwritten from the new fetch, and `Entry.updated_at` (local "last touched" timestamp) advances.
2. **Exception:** any field the user has manually edited in Curate mode (tracked via a per-field `*_locked_by_user` boolean — see §3.3) is **never** overwritten by a resync. E.g., if Brian manually retitled an entry, a future resync that finds a different `og:title` will update `Entry.source_title` (a separate raw-source-mirror column) but leave `Entry.title` (the displayed value) untouched, and will flag `review_status='source_changed_under_edit'` so Brian can see there's a diff to optionally accept.
3. Media reordering/cover selection done manually is similarly locked (`EntryMedia.position_locked`, `EntryMedia.is_cover_locked`) and survives resync; **newly discovered** media on a resync (e.g. a photo added to the live post later) are appended after the highest existing locked position, never inserted in a way that reshuffles a human's ordering.

### 2.7 Expected volume

Computed from the site's own "Archives" widget (every month-bucket count from December 2004 through May 2026, summed):

- **Post count:** **≈1,698 posts** (this is a real computed sum from live data, not a round-number guess; treat it as accurate to within the handful of posts that may be unlisted/private/scheduled). The historical archive crawl in Stage 0 will produce the exact figure on first run; `scrapbook status` should report it next to this estimate so drift is visible immediately.
- **Photos per post:** observed range 1–16 in sampled posts (single-photo posts and 16-photo trip recaps both occur); estimated mean ≈6 images/post.
- **Estimated total media count:** ≈1,698 × 6 ≈ **10,000–12,000 images**, plus an unknown but probably small number of bare-URL video references (not downloaded, just linked — see §2.3 Stage 2).
- **Estimated media storage:** full-resolution travel photos at this site's typical original dimensions observed (~2000×1500 px JPEGs/PNGs) run roughly 1–4 MB each; at a conservative 2.5 MB average × ~11,000 images ≈ **20–35 GB** of media. *(Flagged as an estimate pending the first full backfill — see §11; the actual figure should be captured in `scrapbook status` after Phase 1's first full sync and this PRD's number revised if materially different.)*
- **Estimated crawl time, first full backfill:** ~1,698 post fetches at the politeness floor (1.5–3.0s between requests, concurrency 2) ≈ 45–75 minutes for post HTML alone; ~11,000 media downloads at concurrency 4 with the same per-request floor, dominated by file transfer time more than politeness delay ≈ 2–5 hours depending on local bandwidth. **Total one-time backfill: plan for 3–6 hours, run unattended.**
- **Estimated crawl time, steady-state incremental sync** (every few months, per the operations workflow in `ARCHITECTURE.md`): a handful to ~20 new/changed posts and their media ≈ **2–10 minutes**.

### 2.8 Auto-tagging heuristics (v1)

Run during Stage 4 upsert, additive only (never removes/overrides manual tags):

1. **Date tags** — always applied: `{YYYY}` (e.g. `2026`) and a season tag derived from month. **Hemisphere convention:** Northern Hemisphere meteorological seasons are used — `Dec/Jan/Feb → Winter {year}`, `Mar/Apr/May → Spring {year}`, `Jun/Jul/Aug → Summer {year}`, `Sep/Oct/Nov → Fall {year}` — because Brian's posting pattern during reconnaissance (Netherlands, Turkey, Malta, Ireland, Germany — all Northern Hemisphere) indicates this is his home-base hemisphere even though individual trips range globally; the season tag describes *when* the post was made, not the climate at the destination, so a July post about a Southern Hemisphere trip still gets tagged `Summer {year}` (Brian's seasonal context), not `Winter` (the destination's). This mapping is hardcoded for v1, not config-driven. `type='trip'` is reserved for manual/collection use. Date/season tags use a dedicated `tag.type='date'` value (the CHECK constraint in §3.3 includes `topic`, `person`, `place`, `trip`, `custom`, `date`) — a real, queryable distinction, stored with `type='date'` literally rather than as a naming convention. `--tag-date` (`#4A5868`, 6.09:1 contrast on parchment — verified) is the calendar-icon-chip color for this tag type in §7.2.
2. **Keyword-dictionary topic tags** — a YAML-configurable dictionary (`config/tag_keywords.yaml`) maps keyword sets to `Tag(type='place'|'topic')` rows. Matching is case-insensitive substring/word-boundary match against `title` and the first 500 characters of `body_text` (titles are heavily weighted — most post titles in this blog are literally the destination name, e.g. "Malta, March 2026", "Tenerife, February 2026"). Concrete v1 seed content, built directly from the post titles this PRD's own reconnaissance actually sampled:
   ```yaml
   # config/tag_keywords.yaml — v1 seed dictionary, hand-edited, grows via future curation
   place:
     Turkey: ["turkey", "cappadocia", "istanbul"]
     Malta: ["malta", "valletta", "sliema"]
     Tenerife: ["tenerife", "canary islands", "san cristóbal de la laguna", "santa cruz de tenerife"]
     Ireland: ["dublin", "guinness storehouse"]
     "Las Vegas": ["las vegas", "vegas", "mandalay bay", "excalibur"]
     England: ["brighton"]
     Germany: ["cologne", "köln", "koln"]
     Netherlands: ["netherlands"]
   topic:
     Hiking: ["hike", "hiking", "trail"]
     "Live Music": ["concert", "sting", "message in a bottle"]
     Pets: ["piper", "dog walk", "cows", "horses"]
   ```
   This dictionary ships as the v1 default and is expected to grow via hand-editing (a "promote this manual tag to an auto-rule" Curate-UI affordance is a v1.1 nice-to-have, not required for v1).
3. **Person tags** — not auto-derived in v1 (no reliable signal in the HTML); always manual. The schema supports `Tag(type='person')` fully; population is a Curate-mode activity.

---

## 3. Data Model (complete)

### 3.1 Conventions

- All tables use an `INTEGER PRIMARY KEY` (SQLite rowid alias) for internal joins, plus a separate stable `uuid TEXT UNIQUE` where external/export references are needed (media, entries, collections) so vault bundle exports and any future multi-device sync have stable IDs independent of local rowid ordering.
- All timestamps are stored as ISO-8601 UTC strings (`TEXT`, e.g. `2026-06-20T14:03:11Z`), not Unix integers — readability during manual SQLite inspection/debugging is valued over marginal storage savings at this data volume.
- Foreign keys are enforced (`PRAGMA foreign_keys = ON` set at every connection open, both CLI and API processes).
- Soft-delete via `status` enum columns, not row deletion, except where explicitly noted (preservation principle).
- **Text normalization for search:** WordPress runs `wptexturize()` on all rendered content, converting plain quotes/apostrophes/dashes into "smart" Unicode equivalents (`'` → `’`, `"…"` → `“…”`, `--` → `–`/`—`) — confirmed present in the actual fetched site text during reconnaissance (e.g. curly apostrophes in "it's", em dashes in trip narration). `body_text` (the FTS-indexed plain-text mirror of `body_html`, §2.3 Stage 2 step 4) is generated with these normalized back to plain ASCII equivalents (`’`/`‘`→`'`, `“`/`”`→`"`, `–`/`—`→`-`) **before** indexing, so a search for `we're` matches text that was rendered on the source site as `we’re`. `body_html` itself is left with the original typographic characters intact for display.

### 3.1.1 Resolved deployment-mode ambiguity (see ARCHITECTURE.md "Deployment model")

`ARCHITECTURE.md` describes two valid ways to run the app day-to-day: "a desktop-like app, or a local web app opened in your browser at localhost." This PRD commits v1 to the **second option only** — `scrapbook serve` + system default browser at `http://localhost:8420` (§5, §6). No Electron/Tauri/native desktop shell is built in v1; that remains a legitimate future option (the FastAPI+React stack underneath would not need to change to add one later) but is explicitly out of scope so a developer doesn't wonder whether a desktop wrapper is implicitly required.

### 3.2 Entity-relationship summary

```
Source 1──* IngestRun
Source 1──* Entry
Entry 1──* EntryMedia *──1 Media
Entry *──* Tag   (via EntryTag)
Entry *──* Location (via EntryLocation)
Collection *──* Entry (via CollectionEntry)
Entry 1──1 entries_fts (FTS5 shadow)
```

### 3.3 DDL — core tables

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE source (
    id              INTEGER PRIMARY KEY,
    type            TEXT NOT NULL CHECK (type IN ('wordpress','photo_library','scanned_album','manual')),
    name            TEXT NOT NULL,
    base_url        TEXT,
    config_json     TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (type, name)
);

CREATE TABLE ingest_run (
    id              INTEGER PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES source(id) ON DELETE CASCADE,
    mode            TEXT NOT NULL CHECK (mode IN ('full','incremental')),
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    status          TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','completed','failed','aborted')),
    stats_json      TEXT NOT NULL DEFAULT '{}',   -- counters: posts_seen, posts_new, posts_updated, posts_unchanged, posts_error, media_downloaded, media_deduped, media_error, bytes_downloaded
    error_message   TEXT
);
CREATE INDEX idx_ingest_run_source ON ingest_run(source_id, started_at DESC);

CREATE TABLE entry (
    id                      INTEGER PRIMARY KEY,
    uuid                    TEXT NOT NULL UNIQUE,
    source_id               INTEGER NOT NULL REFERENCES source(id) ON DELETE RESTRICT,
    source_entry_id         TEXT NOT NULL,         -- dedup key part 2 (see §2.6)
    canonical_slug          TEXT NOT NULL,
    source_url              TEXT NOT NULL,
    title                   TEXT NOT NULL,         -- displayed title (may be manually edited)
    source_title            TEXT NOT NULL,         -- last-seen title from source, mirror only
    title_locked_by_user    INTEGER NOT NULL DEFAULT 0,
    body_html               TEXT NOT NULL,         -- with <img src> rewritten to media:// refs
    body_text               TEXT NOT NULL,         -- plain text, feeds FTS
    event_date              TEXT NOT NULL,         -- DATE-ONLY 'YYYY-MM-DD' (no time component — see §2.3), derived from the permalink path, not article:published_time; displayed date, may be manually edited
    source_event_date       TEXT NOT NULL,         -- DATE-ONLY 'YYYY-MM-DD', same derivation, last-seen-from-source mirror
    event_date_locked_by_user INTEGER NOT NULL DEFAULT 0,
    source_updated_at       TEXT,                  -- full ISO-8601 UTC datetime 'YYYY-MM-DDTHH:MM:SSZ' (article:modified_time) — unlike event_date, time precision matters here for resync diffing
    raw_snapshot_path       TEXT NOT NULL,
    shortlink               TEXT,                  -- wp.me/... reference only, not a dedup key
    status                  TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','removed_at_source','parse_error','merged')),
    review_status           TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending','reviewed','possible_duplicate','source_changed_under_edit')),
    possible_duplicate_of   INTEGER REFERENCES entry(id) ON DELETE SET NULL,  -- dual-purpose: candidate match while review_status='possible_duplicate'; becomes "merged into" target when status='merged' (see §8.3 — no separate merged_into column needed)
    cover_media_id          INTEGER REFERENCES media(id) ON DELETE SET NULL,  -- this FK only guarantees the row exists, NOT that it belongs to this entry's entry_media set — that check is application-layer only, enforced by POST /api/entries/{id}/cover (§5.2), since SQLite has no clean way to declaratively CHECK across two tables
    cover_locked_by_user    INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (source_id, source_entry_id)
);
CREATE INDEX idx_entry_event_date ON entry(event_date);
CREATE INDEX idx_entry_status ON entry(status);
CREATE INDEX idx_entry_review_status ON entry(review_status);
CREATE INDEX idx_entry_slug ON entry(canonical_slug);

CREATE TABLE media (
    id              INTEGER PRIMARY KEY,
    uuid            TEXT NOT NULL UNIQUE,
    sha256          TEXT NOT NULL UNIQUE,
    mime_type       TEXT NOT NULL,                  -- 'image/jpeg','image/png','external/video', etc.
    width           INTEGER,
    height          INTEGER,
    duration_sec    REAL,
    byte_size       INTEGER,
    exif_json       TEXT,
    source_url      TEXT NOT NULL,                   -- original normalized URL it was fetched from
    storage_path    TEXT,                             -- NULL for external/video refs and missing_at_source
    status          TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok','missing_at_source','external_reference')),
    derived_from_media_id  INTEGER REFERENCES media(id) ON DELETE SET NULL,  -- nullable self-reference, unpopulated by the connector in v1 (auto-detection is an Open Question, §11.7); column exists now so a future "2 versions of this photo" UI doesn't require a schema migration. Manually settable via Curate mode at any time.
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX idx_media_sha256 ON media(sha256);
CREATE INDEX idx_media_status ON media(status);

CREATE TABLE entry_media (
    entry_id            INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    media_id            INTEGER NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    position             INTEGER NOT NULL DEFAULT 0,
    position_locked       INTEGER NOT NULL DEFAULT 0,
    caption              TEXT,
    is_cover             INTEGER NOT NULL DEFAULT 0,
    is_cover_locked       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (entry_id, media_id)
);
CREATE INDEX idx_entry_media_entry ON entry_media(entry_id, position);

CREATE TABLE tag (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL COLLATE NOCASE,   -- case-insensitive so "Turkey" and "turkey" inserted by different code paths (auto-tagger vs. manual) collide into one row, not two
    type            TEXT NOT NULL CHECK (type IN ('topic','person','place','trip','custom','date')),  -- 'date' covers date/season tags (§2.8) as their own real type
    UNIQUE (name, type)
);
CREATE INDEX idx_tag_type ON tag(type);
-- Note: SQLite's default TEXT collation (BINARY) is case-sensitive, so without COLLATE NOCASE here, "Turkey"/"turkey"/"TURKEY"
-- would each satisfy the UNIQUE(name,type) constraint as distinct rows — exactly the duplicate-tag bug §2.8's case-insensitive
-- keyword matching would otherwise produce. Display casing is still whatever was first inserted (store seed dictionary values
-- in Title Case, e.g. "Turkey" not "turkey", so the canonical display form is controlled even though lookups are case-insensitive).

CREATE TABLE entry_tag (
    entry_id        INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    tag_id          INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
    source          TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual','auto')),
    PRIMARY KEY (entry_id, tag_id)
);
CREATE INDEX idx_entry_tag_tag ON entry_tag(tag_id);

CREATE TABLE location (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    lat             REAL,
    lng             REAL,
    country         TEXT,
    place_id        TEXT,                  -- external geocoder reference, e.g. Nominatim/Google place_id
    UNIQUE (name, country)
);

CREATE TABLE entry_location (
    entry_id        INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    location_id     INTEGER NOT NULL REFERENCES location(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, location_id)
);

CREATE TABLE collection (
    id              INTEGER PRIMARY KEY,
    uuid            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    description     TEXT,
    cover_media_id  INTEGER REFERENCES media(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE collection_entry (
    collection_id   INTEGER NOT NULL REFERENCES collection(id) ON DELETE CASCADE,
    entry_id        INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    position        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (collection_id, entry_id)
);
```

### 3.4 FTS5 virtual table

```sql
CREATE VIRTUAL TABLE entries_fts USING fts5(
    title,
    body_text,
    content='entry',
    content_rowid='id',
    tokenize='porter unicode61 remove_diacritics 2'
);

-- Keep entries_fts in sync with entry via triggers (FTS5 external-content pattern)
CREATE TRIGGER entry_ai AFTER INSERT ON entry BEGIN
    INSERT INTO entries_fts(rowid, title, body_text) VALUES (new.id, new.title, new.body_text);
END;

CREATE TRIGGER entry_ad AFTER DELETE ON entry BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, title, body_text) VALUES ('delete', old.id, old.title, old.body_text);
END;

CREATE TRIGGER entry_au AFTER UPDATE ON entry BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, title, body_text) VALUES ('delete', old.id, old.title, old.body_text);
    INSERT INTO entries_fts(rowid, title, body_text) VALUES (new.id, new.title, new.body_text);
END;
```

Example query (ranked, snippet-highlighted — used by the search endpoint, §5.3):

```sql
SELECT e.id, e.title, e.event_date,
       snippet(entries_fts, 1, '<mark>', '</mark>', '…', 12) AS snippet,
       bm25(entries_fts, 5.0, 1.0) AS rank
FROM entries_fts
JOIN entry e ON e.id = entries_fts.rowid
WHERE entries_fts MATCH 'malta OR valletta'
  AND e.status IN ('active', 'removed_at_source')
ORDER BY rank
LIMIT 20;
```
The column-weight arguments `(5.0, 1.0)` weight `title` 5x over `body_text`. This isn't an arbitrary tuning choice — reconnaissance directly showed that for this specific blog, the title *is* the dominant relevance signal (most post titles are literally the destination name, e.g. "Malta, March 2026"), so a search for "Malta" should rank the post titled "Malta, March 2026" above a different post that merely mentions Malta once in passing body text. (`removed_at_source` entries are still searchable, only `merged`/`parse_error` are excluded — see §5.2's default status-filtering rule.)

Per `ARCHITECTURE.md`'s search strategy ("Start with SQLite FTS5. Optional upgrade later to Tantivy/Meilisearch if needed."), FTS5 is the only search engine built in v1 — at ~1,700 entries and ~25MB of indexed text, FTS5 is comfortably sufficient and a separate search service would be pure overhead. If a future phase ever needs fuzzy/typo-tolerant search or sub-entry (paragraph-level) search, the migration path is additive — `entries_fts` is structured so a future Tantivy/Meilisearch index could be built from the same `entry.body_text` source of truth without changing the `entry` table itself.

### 3.5 Content-addressed media store

```text
data/media/
  {sha256[0:2]}/{sha256[2:4]}/{sha256}.{ext}
data/thumbnails/
  {sha256[0:2]}/{sha256[2:4]}/{sha256}_thumb.webp     # generated lazily, 480px-wide WebP, by `scrapbook reindex --thumbnails`
```

Example: a JPEG with hash `9f8a...c2` lives at `data/media/9f/8a/9f8a...c2.jpg`. The two-level hash-prefix sharding keeps any single directory from accumulating more than a few hundred files even at 12,000+ images (avoids filesystem performance cliffs on common filesystems at >10k entries/directory).

**Naming/extension rule:** the file extension is derived from the detected `mime_type` (via Pillow/`python-magic`), not trusted from the source URL, since Photon-served URLs sometimes carry a misleading extension. `.jpg` for `image/jpeg`, `.png` for `image/png`, `.gif` for `image/gif`, `.webp` for `image/webp`.

**Animated images:** thumbnails are always static (first-frame-only WebP, even for an animated source GIF) — a static preview is sufficient for grid/filmstrip use; the `/full` endpoint (§5.5) always serves the original file's bytes unchanged, so animation is preserved wherever the full image is actually viewed.

**Collision handling:** the `(sha256)` unique constraint on `media` makes "collision" mean "identical file already stored" — this is the desired, expected dedup behavior, not an error. A genuine hash collision (different bytes, same SHA-256) is treated as cryptographically negligible and not specially handled. If a write to `storage_path` fails mid-write (disk full, crash), the connector writes to a `.tmp` sibling first and renames atomically on success, so a partially-written file is never mistaken for a complete one and never gets a `Media` row pointing at it.

### 3.6 Alembic migration strategy

- `core/db/migrations/` is a standard Alembic environment (`alembic.ini` pointing at `sqlite:///data/db/scrapbook.sqlite`).
- **Initial migration** (`0001_initial_schema.py`): contains the full DDL in §3.3–3.4 verbatim (Alembic `op.execute()` blocks for the FTS5 virtual table and triggers, since Alembic's autogenerate does not understand FTS5; everything else can use `op.create_table`/`op.create_index`).
- **Upgrade path convention:** every subsequent schema change is one migration per logical change (not batched), named `{NNNN}_{snake_case_description}.py`, e.g. `0002_add_possible_duplicate_of.py`. Each migration must have a working `downgrade()` — SQLite's limited `ALTER TABLE` means most non-trivial downgrades use the documented "rename table, create new, copy data, drop old" pattern; Alembic's `batch_alter_table` context manager handles this automatically and **must** be used for any column add/drop/type-change on SQLite.
- `scrapbook init` (CLI, §4) runs `alembic upgrade head` against a fresh or existing `data/db/scrapbook.sqlite`, creating the file and directory structure if absent. Every other CLI command checks the current Alembic revision against the code's expected head revision at startup and refuses to run (clear error, exit code 3) if they mismatch, rather than risk operating against a stale schema.

---

## 4. CLI Specification

Built with **Typer** (per `ARCHITECTURE.md`), rich progress bars/tables via **Rich**. Entry point: `scrapbook` (installed console script; during development, `python -m core.cli`).

### 4.1 `scrapbook init`

Initializes the project structure and database. Idempotent — safe to rerun.

```text
scrapbook init [--data-dir PATH] [--config PATH]

--data-dir PATH    Root for data/ (default: ./data, resolved relative to repo root)
--config PATH      Path to sources.yaml (default: ./config/sources.yaml)
```

Output:
```
$ scrapbook init
✔ Created data/db, data/raw, data/media, data/thumbnails, data/exports
✔ Alembic: applying migrations 0001_initial_schema → head (1 applied)
✔ Wrote default config/sources.yaml (1 source: grothadventures)
Ready. Run `scrapbook sync --source grothadventures` to begin.
```
Exit code 0 on success; 1 if `data-dir` exists and is not writable.

### 4.2 `scrapbook sync`

```text
scrapbook sync --source NAME [--full] [--dry-run] [--max-posts N] [--since DATE] [--no-media] [--concurrency N] [--verbose]

--source NAME       Required. Source id from sources.yaml (e.g. "grothadventures")
--full              Force a full historical re-crawl via archive index, ignoring sitemap-only delta hints (default: incremental)
--dry-run           Run discovery + diffing only; report what would change; no fetches of post/media bodies, no DB writes
--max-posts N       Cap the number of post fetches this run (default: unlimited) — useful for testing
--since DATE        Only consider posts with event_date >= DATE (ISO-8601). Only meaningful combined with --full (incremental mode's candidate list is already just "what changed," so --since on its own would be a no-op that could mislead the user into thinking it narrowed something) — using --since without --full is a validation error at startup ("Error: --since requires --full", exit code 1), not a silent no-op
--no-media          Skip Stage 3 media downloads (text/metadata only) — useful for a fast metadata-only refresh
--concurrency N     Override config max_concurrent_requests (default: from sources.yaml)
--verbose           Per-item log lines in addition to the progress bar
```

Example output:
```
$ scrapbook sync --source grothadventures
Groth Adventures sync — incremental mode
✔ robots.txt loaded (politeness: 1.5–3.0s/request, concurrency=2)
✔ sitemap.xml: 143 entries (12 newer than local)
✔ news-sitemap.xml: 1 entry (already known)
Discovery complete: 12 posts to fetch, 0 known removed

Fetching posts   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 12/12 0:00:34
Downloading media ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 58/58 0:02:11

Sync complete in 3m02s
  Posts:  12 new, 0 updated, 0 errors
  Media:  54 new, 4 deduped (already had these bytes), 0 errors
  Storage added: 142.3 MB
  Review queue: 12 entries awaiting review → run `scrapbook review`
```

**`--dry-run` output**, showing discovery/diff results with no fetches or writes:
```
$ scrapbook sync --source grothadventures --dry-run
Groth Adventures sync — DRY RUN (no fetches beyond discovery, no DB writes)
✔ robots.txt loaded
✔ sitemap.xml: 143 entries (3 newer than local)
✔ news-sitemap.xml: 1 entry (already known)

Would fetch 3 posts:
  [changed] 2026/05/27/our-cows-horses/  (source lastmod newer than local)
  [new]     2026/06/15/some-new-post/
  [new]     2026/06/18/another-new-post/

Would skip 140 posts (unchanged).
Dry run complete — no network requests beyond discovery were made, no database rows were written.
```

**`scrapbook sync` output when some items genuinely error:**
```
$ scrapbook sync --source grothadventures
Groth Adventures sync — incremental mode
✔ robots.txt loaded (politeness: 1.5–3.0s/request, concurrency=2)
✔ sitemap.xml: 143 entries (15 newer than local)
Discovery complete: 15 posts to fetch, 0 known removed

Fetching posts   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 15/15 0:00:41
Downloading media ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 71/71 0:02:55

Sync complete in 3m36s — completed WITH 2 errors (see below)
  Posts:  14 new, 1 updated, 0 errors
  Media:  67 new, 2 deduped, 2 errors
  Storage added: 168.9 MB

Errors:
  [INVALID_IMAGE_DATA] media at https://grothadventures.com/wp-content/uploads/2026/06/img_9201.jpg
      → recorded as Media(status='missing_at_source'); will appear in Review Queue
  [HTTP_404_NOT_FOUND] media at https://grothadventures.com/wp-content/uploads/2026/06/img_9202.jpg
      → recorded as Media(status='missing_at_source'); will appear in Review Queue

Review queue: 14 entries awaiting review, 2 broken-image flags → run `scrapbook review`
```
Per §2.4, exit code is still `0` here — per-item errors never fail the overall run.

Exit codes: `0` completed (even with some per-item errors — see §2.4); `1` configuration error (bad/missing source); `2` early-abort due to repeated connection failures (§2.4); `3` schema/migration mismatch.

### 4.3 `scrapbook review`

Opens the Curate app directly to the Review Queue (launches the local API + frontend if not already running, then opens the OS default browser to `http://localhost:8420/curate?filter=pending`). Headless/CI-friendly fallback: `--no-browser` prints the URL instead of opening it; `--list` prints the pending queue as a table without starting the server.

```text
scrapbook review [--no-browser] [--list] [--port N]
```
```
$ scrapbook review --list
Review Queue (12 pending)
┌────┬──────────────────────────┬────────────┬──────────────┐
│ ID │ Title                    │ Date       │ Status       │
├────┼──────────────────────────┼────────────┼──────────────┤
│ 1701│ Our Cows & Horses       │ 2026-05-27 │ pending      │
│ 1700│ Turkey, May 2026        │ 2026-05-12 │ pending      │
│ ... │ ...                     │ ...        │ ...          │
└────┴──────────────────────────┴────────────┴──────────────┘
```

### 4.4 `scrapbook status`

```text
scrapbook status [--source NAME] [--json]
```
```
$ scrapbook status
Groth Adventures Offline Scrapbook
Database: data/db/scrapbook.sqlite (schema rev: 0001_initial_schema, up to date)

Source: grothadventures
  Entries:      1698 active, 0 removed_at_source, 1 parse_error
  Media:        10,944 ok, 3 missing_at_source, 12 external_reference
  Storage:      data/media = 24.1 GB, data/raw = 3.7 GB, data/db = 412 MB
  Last sync:    2026-06-20T14:03:11Z (incremental, 3m02s, 0 errors)
  Review queue: 12 pending, 1 possible_duplicate

Run `scrapbook review` to clear the review queue.
```
**`--json` output schema** (load-bearing: `scripts/monthly_update.ps1`/`.sh`, §10 Phase 2 task 2.8, parses specific fields out of this):
```json
{
  "database": { "path": "data/db/scrapbook.sqlite", "schema_revision": "0001_initial_schema", "up_to_date": true },
  "source": {
    "id": "grothadventures",
    "entries": { "active": 1698, "removed_at_source": 0, "parse_error": 1, "merged": 0 },
    "media": { "ok": 10944, "missing_at_source": 3, "external_reference": 12 },
    "storage_bytes": { "media": 25879842816, "raw": 3972845568, "db": 432013312 },
    "last_sync": { "started_at": "2026-06-20T14:00:09Z", "completed_at": "2026-06-20T14:03:11Z", "mode": "incremental", "duration_sec": 182, "errors": 0 },
    "review_queue": { "pending": 12, "possible_duplicate": 1, "source_changed_under_edit": 0 }
  }
}
```
`scripts/monthly_update.ps1`/`.sh` (§10 task 2.8) specifically reads `source.review_queue.pending` and `source.entries.parse_error` (plus `source.last_sync.errors`) to decide what to print in its end-of-run summary — these three fields are load-bearing for that script and must not be renamed without updating it.

### 4.5 `scrapbook reindex`

Rebuilds derived data without re-crawling the network. Used after a parser bugfix, a tagging-dictionary change, or to (re)generate thumbnails.

```text
scrapbook reindex [--fts] [--thumbnails] [--tags] [--reparse-snapshots] [--entry-id ID]

--fts                  Rebuild the entries_fts index from current entry rows
--thumbnails            Generate thumbnails that don't exist yet in data/thumbnails (skips any sha256 that already has a thumbnail file)
--thumbnails --force   Regenerate ALL thumbnails unconditionally, including ones that already exist — needed after a thumbnail-rendering code or quality-setting change, otherwise old WebP files would never get refreshed
--tags                  Re-run auto-tagging heuristics against current tag_keywords.yaml (additive; never touches source='manual' tags)
--reparse-snapshots     Re-run HTML/JSON extraction against the stored raw snapshots (no network), updating entries whose parser output would change — used after fixing a MALFORMED_HTML class of bug
--entry-id ID           Limit any of the above to a single entry (debugging)
```
```
$ scrapbook reindex --reparse-snapshots --tags
Reparsing 1 snapshot(s) flagged parse_error ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1/1
  Entry 1432 "December Dublin" — parse_error resolved ✔
Re-tagging 1698 entries ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1698/1698
  +212 new auto tags applied, 0 manual tags touched
Done in 8.4s
```

### 4.6 `scrapbook export`

```text
scrapbook export --format bundle [--output PATH] [--collection NAME] [--since DATE] [--no-raw-snapshots]

--format bundle         Only supported format in v1 (see §9)
--output PATH            Destination directory (default: data/exports/vault-{timestamp}/)
--collection NAME        Export only entries in a named collection (default: everything). If NAME doesn't match any existing collection, exit code 4 (resource not found, §4.10) with "Error: collection \"NAME\" not found. Open the app and check Curate → Collections for exact names." — note there is intentionally no CLI command to list/manage collections (they're a browsing/curation concept, managed entirely via the API/UI per §5.4, not a CLI concern)
--since DATE             Export only entries with event_date >= DATE
--no-raw-snapshots       Exclude data/raw from the bundle (smaller, but loses reprocessing ability — not recommended for a backup bundle, useful for a quick "send a few entries to Lorie's laptop" export)
--prune-older-than N     Optional v1.1 nice-to-have, not built in v1 (see §9.5): would delete verified bundles under data/exports/ older than N days. Listed here only so the flag name is reserved/consistent if implemented later.
```
```
$ scrapbook export --format bundle
Building vault bundle → data/exports/vault-20260620-140500/
✔ Copying 1698 entries, 10,944 media files (24.1 GB)
✔ Writing manifest.json + checksums.sha256
✔ Verifying checksums                    ━━━━━━━━━━━━━━━━━━━━━━━━ 10944/10944
Bundle complete: data/exports/vault-20260620-140500/ (24.3 GB, verified)
Next step: copy this directory to your backup drive/cloud target.
```

### 4.7 `scrapbook serve`

Starts the FastAPI app (§5) and serves the built React frontend (§6) at `http://localhost:<port>`, against the live `data/` directory by default.

```text
scrapbook serve [--port N] [--data-dir PATH] [--no-browser] [--self-check]

--port N          Port to bind (default: 8420)
--data-dir PATH   Serve against an alternate data directory instead of the live ./data (this is exactly what `scrapbook open-bundle`, §4.9, does under the hood)
--no-browser      Don't auto-open the system default browser on start
--self-check      Run the offline-asset self-check (§6.10) against the built frontend bundle before starting, and exit non-zero without serving if any non-localhost reference is found
```
```
$ scrapbook serve
✔ Offline self-check passed (0 external references found)
Serving Groth Adventures Offline Scrapbook at http://localhost:8420
Press Ctrl+C to stop.
```
Binds to `127.0.0.1` only, never `0.0.0.0` (§5). Exit codes: `0` clean shutdown (Ctrl+C); `1` port already in use or `--data-dir` not a valid scrapbook data directory; `2` `--self-check` failed.

### 4.8 `scrapbook verify-bundle`

```text
scrapbook verify-bundle PATH
```
Re-hashes every file under `PATH` and compares against `PATH/checksums.sha256` and `PATH/manifest.json.sha256` (§9.3). Exit code `0` if every file matches; `2` if any file is missing or its hash differs (prints the specific failing relative paths, never just "verification failed").
```
$ scrapbook verify-bundle /Volumes/Backup/vault-20260620-140500
Verifying 10,945 files ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10945/10945
✔ All files match checksums.sha256
✔ manifest.json matches manifest.json.sha256
Bundle is intact.
```

**Failure case**, demonstrating that specific failing paths are reported, not a generic message:
```
$ scrapbook verify-bundle /Volumes/Backup/vault-20260620-140500
Verifying 10,945 files ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10945/10945
✘ 2 file(s) failed verification:
  media/9f/8a/9f8a3c2e...d92e.jpg  — hash mismatch (expected 9f8a3c2e..., got a14bcf01...)
  raw/grothadventures/2018/10/15-malta-day-one/response.html — file missing
Bundle is DAMAGED. 10,943/10,945 files verified successfully.
```
Exit code `2` in this case, per §4.8's existing exit-code table.

### 4.9 `scrapbook open-bundle`

```text
scrapbook open-bundle PATH [--port N] [--no-browser]
```
Convenience wrapper: runs `scrapbook verify-bundle PATH` first (warns but does not block on a failed verification — a slightly damaged bundle should still be browsable for inspection), then `scrapbook serve --data-dir PATH/db/.. --port N`. This is how a vault bundle (§9) is actually opened/browsed months or years later, including on a different machine than the one that created it.

### 4.10 Global flags & exit codes

All commands accept `--config PATH`, `--data-dir PATH`, `--log-level [debug|info|warning|error]`. Standard exit codes across the CLI:

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Configuration/argument error (bad source name, bad path) |
| 2 | Runtime failure during execution (network abort, disk full) |
| 3 | Database schema mismatch (migrations not applied / code-vs-schema version skew) |
| 4 | Resource not found (e.g. `--entry-id` doesn't exist) |

---

## 5. Local API (FastAPI) — for the UI

Runs at `http://localhost:8420` (configurable), bound to `127.0.0.1` only — never `0.0.0.0` — since this is a single-PC tool with no auth layer; binding to localhost-only is the security boundary. Started by `scrapbook serve` (a thin CLI wrapper not detailed separately above) or implicitly by `scrapbook review`.

### 5.1 Conventions

- All responses are JSON, `Content-Type: application/json`.
- Pagination: cursor-based on all list endpoints — `?cursor=<opaque>&limit=<int, default 30, max 100>`. Response envelope:
```json
{
  "items": [ /* ... */ ],
  "next_cursor": "eyJpZCI6MTY4NX0=",
  "has_more": true
}
```
The cursor encodes the last-seen `(sort_key, id)` pair base64'd; clients treat it as opaque. First page omits `cursor`.

**Tie-breaking:** `event_date` is date-only (§2.3/§3.3), so multiple entries routinely share the exact same value (e.g. several posts from one multi-day trip with backdated identical dates) — every cursor-paginated query therefore uses composite keyset pagination — `id` as an explicit, deterministic secondary sort key in the *same* direction as the primary sort, e.g. for the default `event_date_desc`:
```sql
SELECT * FROM entry
WHERE status IN ('active', 'removed_at_source')
  AND (event_date, id) < (:cursor_event_date, :cursor_id)   -- omitted entirely on the first page
ORDER BY event_date DESC, id DESC
LIMIT :limit;
```
The cursor for the next page is `base64({"sort_key": "<last_row.event_date>", "id": <last_row.id>})`. This guarantees every row is returned exactly once across a full pagination walk, even with many same-`event_date` ties.
- Errors: `{"error": {"code": "ENTRY_NOT_FOUND", "message": "Entry 9999 does not exist"}}` with matching HTTP status (404/400/409/500).

### 5.2 Endpoints — Entries

**`GET /api/entries`** — list, default sorted `event_date DESC`.
Query params: `cursor`, `limit`, `year` (int), `tag` (repeatable, e.g. `?tag=place:Malta&tag=topic:Hiking`, AND semantics), `collection_id`, `sort` (`event_date_desc` default | `event_date_asc` | `updated_at_desc`).

**`tag` parsing rule:** each `tag` value (format `{type}:{name}`) is split on the *first* `:` into `(type, name)` (so a tag name containing a colon, while unlikely, still parses correctly — only the first colon is the delimiter); `type` is matched exactly against `tag.type`'s enum, `name` is matched against `tag.name` using its existing `COLLATE NOCASE` (§3.3), case-insensitively. If a given `tag` value matches no row in the `tag` table, that filter clause contributes **zero results** for that tag (not a 400 error) — a typo'd or stale tag name should narrow results to nothing, not fail the whole request.

**Default `status` filtering:** every list/search endpoint (`GET /api/entries`, `GET /api/search`, Timeline's data source) defaults to `WHERE entry.status IN ('active', 'removed_at_source')` — `removed_at_source` entries browse completely normally (the whole point of local preservation is that they're still here even if the live site deleted them; see §6.3 for the small UI badge this implies), while `'merged'` (absorbed into another entry — showing it would just be a confusing duplicate) and `'parse_error'` (extraction failed, not yet fixed — showing broken/empty content would be worse than hiding it) are excluded from every default view. `parse_error` entries remain reachable directly by ID and via `scrapbook status`/the Review Queue.

Example response item:
```json
{
  "id": 1701,
  "uuid": "5c2e...",
  "title": "Our Cows & Horses",
  "event_date": "2026-05-27",
  "cover_media": { "id": 9821, "thumb_url": "/api/media/9f8a.../thumb", "width": 2000, "height": 1500 },
  "tags": [ {"id": 4, "name": "2026", "type": "custom"}, {"id": 12, "name": "Spring 2026", "type": "custom"} ],
  "excerpt": "On our evening dog walk, we got to see our local cows and their new(ish) young cows…"
}
```

**`GET /api/entries/{id}`** — full entry detail.
```json
{
  "id": 1701,
  "uuid": "5c2e...",
  "title": "Our Cows & Horses",
  "body_html": "<p>On our evening dog walk... <img src=\"/api/media/9f8a.../full\"/> ...</p>",
  "event_date": "2026-05-27",
  "source_url": "https://grothadventures.com/2026/05/27/our-cows-horses/",
  "review_status": "reviewed",
  "media": [
    {"id": 9821, "position": 0, "is_cover": true, "url": "/api/media/9f8a.../full", "thumb_url": "/api/media/9f8a.../thumb", "width": 2000, "height": 1500, "caption": null}
  ],
  "tags": [ {"id": 4, "name": "2026", "type": "custom", "source": "auto"} ],
  "locations": []
}
```

**`PATCH /api/entries/{id}`** — curation edit (Curate mode, §8). Body is a partial update; any field present locks it (`*_locked_by_user = true`):
```json
{ "title": "Our Cows & Horses (Spring Pasture)", "event_date": "2026-05-27", "cover_media_id": 9822 }
```
Response: the full updated entry (same shape as GET). `409 Conflict` if `If-Match`-style optimistic concurrency fails (client sends the entry's `updated_at` it last read as `expected_updated_at`; mismatch → 409 with the current server copy, so two browser tabs editing the same entry don't silently clobber each other). Example `409` response body:
```json
{
  "error": { "code": "STALE_UPDATE", "message": "Entry 1701 was modified since you last loaded it." },
  "current": { "id": 1701, "title": "Our Cows & Horses (edited in another tab)", "updated_at": "2026-06-20T15:02:44Z", "...": "...full entry, same shape as GET" }
}
```
**Validation:** `entry.title` is `NOT NULL` at the DB layer, but that alone doesn't stop someone from saving an empty string — a `title` value that is empty or whitespace-only after trimming is rejected with `400 {"error": {"code": "VALIDATION_ERROR", "message": "title cannot be empty"}}`, both client-side (so Curate mode's inline editor never even submits it) and server-side (so the API is the actual source of truth for this rule, not just the UI).

**`POST /api/entries/{id}/tags`** `{"tag_id": 12}` / **`DELETE /api/entries/{id}/tags/{tag_id}`** — add/remove a tag (always `source='manual'` via this endpoint).

**`POST /api/entries/{id}/locations`** `{"location_id": 7}` / **`DELETE /api/entries/{id}/locations/{location_id}`** — add/remove a location link (§8.1 Location-tagging flow; mirrors the tags pair above, creating the `EntryLocation` row).

**`POST /api/entries/{id}/media/reorder`** — `{"media_ids": [9822, 9821, 9823]}` → sets `position` in array order and `position_locked=true` for all listed.

**`POST /api/entries/{id}/cover`** — `{"media_id": 9822}` → sets `cover_media_id`, `cover_locked_by_user=true`.

**`POST /api/entries/{id}/review`** — `{"action": "approve"}` | `{"action": "merge_into", "target_entry_id": 1432}` | `{"action": "dismiss_duplicate_flag"}` — review-queue actions (§8.3). `merge_into` sets the source entry's `status='merged'` and `possible_duplicate_of=target_entry_id` (the same column dual-purposed, §3.3) and reassigns its `EntryMedia`/`EntryTag` rows to the target. Both `entry_media` and `entry_tag` have composite primary keys `(entry_id, media_id)`/`(entry_id, tag_id)`, so naively re-pointing the source's rows to the target's `entry_id` would throw a primary-key violation the moment the target already happens to have that same `media_id`/`tag_id` (e.g. both entries already share a reused photo) — so the reassignment is "move-or-merge-on-conflict," not a blind `UPDATE`: for each of the source's `entry_media`/`entry_tag` rows, attempt to re-point it to `target_entry_id`; if a row already exists there for that `(target_entry_id, media_id)` / `(target_entry_id, tag_id)`, **delete** the source's now-redundant row instead of inserting a duplicate (the target keeps its own existing link; nothing is lost, since the same media/tag is already represented). Re-pointed `entry_media` rows are appended after the target's current highest `position` (never reshuffling the target's existing manually-set order). `status='merged'` entries are excluded from all default list/search results (treated like `removed_at_source` for display purposes, but distinguishable for audit) — see §5.2's `status` filtering rule above for what *is* shown by default.

**`POST /api/entries/bulk-tag`** — `{"entry_ids": [1432, 1501, 1602], "tag_id": 12, "action": "add"}` (or `"action": "remove"`) — applies/removes one tag across a set of entries in a single request, always `source='manual'`. Powers the Bulk Tag panel (§8.2). Response: `{"updated_count": 3, "skipped_count": 0}` (an entry already having the tag, on `"add"`, counts as updated-idempotently, not skipped; an entry not having the tag, on `"remove"`, counts as skipped). Capped at 500 `entry_ids` per call (the UI's "select all matching filter" affordance paginates into batches of 500 if a filter matches more than that — unlikely at ~1,700 total entries, but specified so it's not undefined behavior). Exceeding 500 returns `400 {"error": {"code": "BULK_LIMIT_EXCEEDED", "message": "Maximum 500 entry_ids per request, got 612"}}`.

### 5.3 Search

**`GET /api/search`** — `?q=<text>&tag=...&year=...&cursor=...&limit=...`

Translates `q` into an FTS5 `MATCH` expression: tokenized on whitespace (not on hyphens — see escaping rule below), each token wrapped in double quotes, multi-token queries become an implicit `AND` of phrase-quoted tokens (e.g. `q=malta sting` → `entries_fts MATCH '"malta" AND "sting"'`); a leading `"..."` quoted phrase in `q` is passed through as a literal FTS phrase query. Ranking uses `bm25(entries_fts, 5.0, 1.0)` (title-weighted, §3.4); results include the `snippet()` highlight shown in §3.4.

**Escaping rule:** FTS5 treats an unquoted `-` as a column-exclusion operator (which would silently mis-parse a query like `father-in-law`), and a literal `"` character inside the user's query (e.g. searching for `the "best" beach`) could produce malformed FTS5 syntax if not escaped. Tokenizing on whitespace only (never splitting on `-`) and wrapping every token in double quotes already neutralizes FTS5's `-`/`OR`/`AND`/`NOT` operator characters, since anything inside an FTS5 quoted string is treated as a literal — so `father-in-law` becomes the single literal phrase token `"father-in-law"`, not three operator-split words. Any literal `"` character within a token is escaped by doubling it (`"` → `""`, FTS5's own quoted-string escape convention) before the token is wrapped — so `the "best" beach` tokenizes to `"the" AND """best""" AND "beach"`, which FTS5 parses as the literal words `the`, `"best"` (with the quotes as literal characters), `beach`.

```json
{
  "items": [
    {"id": 1432, "title": "December Dublin", "event_date": "2025-12-11",
     "snippet": "...we did the Guinness <mark>Connoisseur</mark> Experience...", "score": 0.83}
  ],
  "next_cursor": null,
  "has_more": false,
  "query_interpreted": "\"connoisseur\""
}
```

### 5.4 Tags, Locations, Collections, Stats

- `GET /api/tags?type=place` — list tags, with `entry_count` per tag, for faceted filter UI.
- `GET /api/locations` — for map view (v2); returns `{name, lat, lng, entry_count}[]`.
- `GET /api/collections`, `POST /api/collections`, `PATCH /api/collections/{id}`, `POST /api/collections/{id}/entries` (reorder/add).
- `GET /api/stats` — powers the Home/TOC year overview: `{"by_year": [{"year": 2026, "count": 8}, ...], "total_entries": 1698, "total_media": 10944, "date_range": ["2004-12-01","2026-05-27"]}`. **`total_media` counts only `media.status='ok'` rows** (actual stored files) — `missing_at_source` and `external_reference` rows are excluded from this figure, matching how `scrapbook export`'s progress count works (§4.6); a separate `total_media_all_statuses` field is not exposed in v1 but the distinction is called out here so whoever implements this endpoint doesn't have to guess which count was intended.
- `GET /api/review-queue` — `?status=pending|possible_duplicate|source_changed_under_edit`, same envelope as `/api/entries`.

### 5.5 Media serving

**`GET /api/media/{sha256}/full`** — streams the original file straight from `data/media/{sha256[0:2]}/{sha256[2:4]}/{sha256}.{ext}` via `FileResponse`, with `Cache-Control: public, max-age=31536000, immutable` (content-addressed → safe to cache forever) and correct `Content-Type` from the stored `mime_type`.

**`GET /api/media/{sha256}/thumb`** — streams `data/thumbnails/.../{sha256}_thumb.webp`; if absent, generates it on-demand synchronously (480px-wide WebP via Pillow), caches to disk, then serves — so `scrapbook reindex --thumbnails` is an optional warm-up, not a hard requirement.

**Non-`ok` media statuses:**
- `status='external_reference'` (a detected YouTube/Vimeo link, §2.3): `GET /api/media/{sha256}/full` and `/thumb` both return `200` with `Content-Type: application/json`, body `{"type": "external_reference", "provider": "youtube", "url": "https://youtube.com/shorts/..."}`, instead of a binary stream. The frontend's media-rendering component checks for this JSON shape and renders a "▶ Watch on YouTube" link/thumbnail-placeholder instead of an `<img>`/`<video>` tag — it never attempts to treat the response as image bytes.
- `status='missing_at_source'` (a 404'd image at ingest time, §2.4): both endpoints return `404` with the standard error envelope (§5.1), `{"error": {"code": "MEDIA_MISSING_AT_SOURCE", "message": "..."}}`. The frontend catches this specific code and renders a "broken image" placeholder with a small Curate-mode-only "relink or remove" affordance (§2.4), rather than a raw broken-image browser icon.

The frontend never constructs `data/media/...` paths itself; all of `body_html`'s rewritten `<img>` tags and every media reference returned by the API use these `/api/media/{sha256}/...` URLs, so the **only** offline-asset rule the frontend needs to know is "everything is same-origin, nothing is remote" (§6.7).

---

## 6. Frontend Specification

> ⚠️ **Largely superseded — see §0.1.** The Home/Timeline/Entry/Search surfaces
> specified here were built and then replaced by the book UI (cover → two-page
> spreads, dual tables of contents, chapter threads). Still accurate: the React +
> Vite stack, same-origin API under `/api/*`, and the offline-asset rules.
> Now also true: the build is a **single self-contained `index.html`** using
> **hash routing**, so the same bundle runs from `file://` (§0.2).

React + Vite, single-page app served by the FastAPI process at `/` (static build) with the API under `/api/*`, both on `localhost:8420` — no CORS configuration needed since it's same-origin.

### 6.1 Home / Table of Contents

**Layout:** A "cabinet" of drawers — one drawer per year, newest first, each drawer showing its post count and, when expanded, a polaroid-style grid of cover photos with title/date. Three tabs above the cabinet switch the grouping: **By Year** (default), **By Trip/Collection**, **By Topic/People/Places** (the same drawer metaphor, just grouped by `Collection` or `Tag` instead of year).

**Components:** `YearDrawer`, `PolaroidThumb` (cover photo + title + date, slight CSS rotation `±1.5deg` per card seeded by entry id for a "scattered on a table" feel without true randomness on every render — exact deterministic formula: `rotation_deg = (entry.id % 7 - 3) * 0.5`, which yields one of `{-1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5}` based purely on `id`, so the same card always renders at the same angle across reloads without needing to store anything), `TabSwitcher`.

**Data:** `GET /api/stats` for the year list/counts (drawer headers render instantly without fetching entries); `GET /api/entries?year=N` lazily when a drawer expands.

**Interactions:** click a drawer header to expand/collapse (animated height, `prefers-reduced-motion` disables the animation); click a `PolaroidThumb` to navigate to the Entry page; keyboard: `Tab`/`Shift+Tab` moves between drawer headers and thumbs, `Enter`/`Space` expands a focused drawer or opens a focused thumb.

### 6.2 Timeline

**Layout:** vertical chronological stream, newest at top, a persistent left-side year/month rail (sticky, click to jump). Each entry renders as a horizontal "scrapbook page" card: cover photo on one side, title/date/excerpt/tag-chips on the other, alternating left/right photo placement per row for visual rhythm.

**Components:** `TimelineRail` (sticky nav, highlights current scroll position's year/month), `TimelineCard`.

**Data:** `GET /api/entries?sort=event_date_desc&cursor=...` — infinite scroll, fetching the next page ~600px before the user reaches the current last card (IntersectionObserver).

**Interactions:** `j`/`k` (or `↓`/`↑`) move focus to next/previous card; `Enter` opens the focused entry; clicking a rail month jumps via the card nearest that month's first entry (smooth-scroll, instant if `prefers-reduced-motion`).

### 6.3 Entry page

**Layout:** parchment-textured page background; title set in display serif; date/location/tag chips beneath title; body text in a readable serif column (max-width ~38rem); **all photos displayed in a grid gallery section below the prose — `<img>` tags are stripped from `body_html` before rendering the prose column, and every photo for the entry is shown exclusively in the gallery grid.** Rationale: WordPress embeds the same images that appear on the navigation/TOC tile as the first image(s) in the post body, causing the cover photo to appear twice on the page (once as the tile, again at the top of the prose). Separating prose from photos eliminates this duplication and gives photos the full-width gallery treatment they deserve rather than being constrained to the prose column width.

**Components:** `EntryHeader` (title, date, tag chips, edit-pencil icon that's only visible/active in Curate mode, and a small "no longer on grothadventures.com" badge rendered when `entry.status === 'removed_at_source'`, since `removed_at_source` entries are shown normally by default per §5.2 but a reader should know the live source no longer has this post), `EntryBody` (renders `body_html` — sanitized). **Sanitizer allowlist** — over ~1,700 posts spanning 20 years, at least some posts are likely to use `<ul>`/`<ol>`/`<li>` (e.g. a packing list or itinerary), `<br>`, in-post subheadings, or a bare `<span>`, so the allowlist covers all of these rather than just the minimal set — `<p>`, `<img>`, `<em>`, `<strong>`, `<a>`, `<blockquote>`, `<figure>`, `<figcaption>`, `<ul>`, `<ol>`, `<li>`, `<br>`, `<hr>`, `<h3>`, `<h4>`, `<span>` (h1/h2 stay reserved for the app's own chrome). `<script>`, `<style>`, `<iframe>`, every `on*` event-handler attribute, and every `style=` attribute are stripped unconditionally regardless of tag, even though the source is "trusted" personal content — raw scraped HTML is never blindly trusted. Concrete example:
```html
<!-- input body_html fragment -->
<p onclick="alert(1)">Packing list:</p>
<ul><li>Passport</li><li>Sunscreen</li></ul>
<script>steal_cookies()</script>
<span style="color:red">Don't forget the dog!</span>

<!-- sanitized output -->
<p>Packing list:</p>
<ul><li>Passport</li><li>Sunscreen</li></ul>
<span>Don't forget the dog!</span>
```
`PhotoLightbox` (click any image → fullscreen slideshow, see §6.5), `PrevNextNav` (chronological prev/next entry links at the bottom, mirroring the source theme's behavior observed during reconnaissance).

**Data:** `GET /api/entries/{id}`.

**Interactions:** click any photo → opens `PhotoLightbox` at that photo; `←`/`→` in lightbox navigates photos within the entry; `Esc` closes; clicking a tag chip navigates to Search pre-filtered by that tag.

### 6.4 Search

**Layout:** a search bar styled like a library card-catalog drawer label; left sidebar of facet filters (Year range slider, Tag checkboxes grouped by type, Has-location toggle); main area is a results list (reuses `TimelineCard` in a denser variant) with the matched-text snippet shown beneath the excerpt.

**Components:** `SearchBar` (debounced 250ms), `FacetSidebar`, `ResultCard` (extends `TimelineCard` with `snippet` prop).

**Data:** `GET /api/search?q=...&tag=...&year=...`; `GET /api/tags` to populate facet checkboxes with counts.

**Interactions:** typing live-updates results (debounced); `Enter` is a no-op (already live) but supported for muscle memory; facet changes update the URL query string so searches are bookmarkable/back-button-able.

### 6.5 Map view (v2 — stub in v1)

v1 ships a disabled "Map" tab with a tooltip "Coming in v2 — needs geocoded locations" and a Curate-mode affordance to start tagging entries with `Location` rows so v2 has data to render against on day one. v2 design intent (not built now): Leaflet or MapLibre with OpenStreetMap tiles (cacheable for true offline use — see §11 open question on offline tile strategy), one pin per distinct `Location`, clustering pins with many entries, click pin → filtered entry list.

### 6.6 Curate mode

Covered fully in §8; navigationally it's a mode toggle (top-right "Curate" switch) that overlays edit affordances onto the same Home/Timeline/Entry views rather than being a wholly separate set of screens, plus the dedicated Review Queue screen.

### 6.7 Visual design system (summary — full detail in §7)

Parchment background (`#F3EAD8` base with a subtle paper-grain SVG noise overlay, see §7.2), ink-brown text (`#2B2118`), accent green (`#138127` — pulled directly from the live site's own `meta-theme-color`, a deliberate nod connecting the archive to its source), serif display face for titles, serif text face for body, polaroid-bordered photo treatment (white border, 2px ink-brown hairline, subtle drop shadow, slight per-card rotation), "cabinet/drawer" metaphor for the TOC, "trading card" tag chips.

### 6.8 Keyboard navigation spec

| Key | Context | Action |
|---|---|---|
| `/` | Anywhere | Focus the search bar (global, like GitHub) |
| `g h` | Anywhere | Go Home/TOC |
| `g t` | Anywhere | Go Timeline |
| `j` / `k` or `↓`/`↑` | Timeline, Search results | Next/previous card |
| `Enter` | Focused card/thumb | Open entry |
| `←` / `→` | Entry page, Lightbox | Previous/next photo (lightbox) or previous/next entry (page, when not in lightbox) |
| `Esc` | Lightbox, any modal | Close |
| `Tab` / `Shift+Tab` | Anywhere | Standard focus order (drawers → thumbs/cards → controls) |
| `c` | Entry page | Toggle Curate mode for this entry |

### 6.9 Slideshow / gallery spec

`PhotoLightbox`: fullscreen overlay, dark scrim (`rgba(20,16,12,0.92)`), current photo centered and scaled to fit viewport minus a caption bar; thumbnail filmstrip along the bottom for the current entry's photos with the active one highlighted; auto-advance optional (off by default; a play/pause control enables a 4s-per-photo auto-advance, pausing on any manual navigation); supports touch swipe (for the eventual case of a touchscreen PC) and mouse-wheel horizontal scroll on the filmstrip; preloads the next and previous full-resolution image while the current one displays, so navigation feels instant despite multi-MB originals.

### 6.10 Offline asset strategy

Everything renders from `/api/media/...` (same-origin, §5.5); no `<img>`, `<video>`, font, or stylesheet in the built frontend references any external host. Fonts are self-hosted (woff2 files bundled in the Vite build, not loaded from Google Fonts at runtime) — this is a hard requirement, not a nicety, since the whole point of the product is zero network dependency after sync. A startup self-check (`scrapbook serve --self-check`, or an automated test in CI) crawls the built frontend bundle for any `http(s)://` reference outside `localhost`/relative paths and fails the build if one is found.

---

## 7. UX & Visual Design Language

> ⚠️ **Palette superseded — intent preserved.** The "physical artefact, not a
> blog theme" intent below is exactly what shipped, but the green-on-parchment
> system was replaced. The book uses **dark leather and desk tones** around
> **warm parchment pages** (`--paper #f9f3e7`, `--ink #2c1810`, `--brown #8b6f4e`,
> gold `#d9b566` for cover embossing), with per-chapter accent colours stored on
> each chapter tag. Typography as specified: Playfair Display (display), Lora
> (body), Inter (UI), all self-hosted — and now **inlined into the bundle** so
> they survive the `file://` export. See `app/src/styles/theme.css` for the
> authoritative tokens.

### 7.1 Design intent

The product exists because a 20-year personal archive deserves to feel like something kept, not something rendered by a generic blog theme. The direction is a **physical scrapbook digitized**: parchment pages, photo corners, hand-labeled drawers — but restrained enough to stay legible and fast, not a kitsch skin. The green accent family (`#138127` for fills/icons, `#0D5C1C` for text — see §7.2) is deliberately inherited from the live site's own `theme-color` meta tag, so the offline archive reads as a continuation of the original blog's identity rather than a totally different product.

### 7.2 Color system

| Token | Hex | Use | Contrast on `--parchment-base` |
|---|---|---|---|
| `--parchment-base` | `#F3EAD8` | Page background | — |
| `--parchment-shadow` | `#E4D6B8` | Drawer/card recessed backgrounds, hover states | — |
| `--ink` | `#2B2118` | Primary text | 13.18:1 ✅ AA body |
| `--ink-soft` | `#5C4A38` | Secondary text, captions, metadata | 7.05:1 ✅ AA body |
| `--accent-green` | `#138127` | **Non-text/large-only uses**: button fills (with white text on top, see below), active-state backgrounds, icons ≥24px, decorative underlines. Sourced from the live site's theme color. | 4.19:1 — passes AA *large-text only* (3:1), **fails** AA body text (4.5:1) |
| `--accent-green-dark` | `#0D5C1C` | **Inline links and any body-sized green text** — this is the one actually used for `<a>` text color, not `--accent-green` | 6.85:1 ✅ AA body |
| `--accent-green` on white-text buttons | `#138127` bg / `#FFFDF7` text | Primary button fill | 4.92:1 ✅ AA body (checked as background, not foreground, contrast) |
| `--polaroid-white` | `#FFFDF7` | Photo border/mat color | — |
| `--tag-place` | `#8A5A3B` | Place-type tag chips (warm brown) | 4.87:1 ✅ AA body |
| `--tag-topic` | `#3B6E8A` | Topic-type tag chips (muted blue) | 4.64:1 ✅ AA body |
| `--tag-person` | `#8A3B6E` | Person-type tag chips | 5.99:1 ✅ AA body |
| `--tag-trip` | `#4D6029` | Trip-type tag chips (darkened olive — see note) | 5.82:1 ✅ AA body |
| `--tag-custom` | `#6E5C3C` | Custom-type tag chips (darkened tan — see note) | 5.39:1 ✅ AA body |
| `--tag-date` | `#4A5868` | Date/season-type tag chips, calendar-icon styling (`type='date'`, §2.8/§3.3, is its own tag type) | 6.09:1 ✅ AA body |

**Contrast verification note:** every token in the table above was checked computationally against WCAG 2.1's relative-luminance formula, not just eyeballed. `--accent-green` (#138127, 4.19:1) is below the 4.5:1 body-text AA threshold, so its use is restricted to non-text/large-only contexts (button fills, icons ≥24px); `--accent-green-dark` (#0D5C1C, 6.85:1) is the color actually used for inline link/body text. Re-run this check (a ~15-line script) any time a token's hex value changes.

Background texture: a tiled, very-low-contrast SVG paper-grain pattern (subtle fiber/noise, opacity ≤6%) over `--parchment-base`, generated once and bundled (not a runtime canvas filter, to keep rendering cheap on every page).

### 7.3 Typography

- **Display/headings:** a humanist serif with character — e.g. **Playfair Display** (bundled self-hosted woff2, §6.10) for entry titles and section headers, weight 600/700, slightly tighter letter-spacing for large sizes.
- **Body text:** a highly readable text serif — e.g. **Crimson Pro** or **Lora**, 400/500 weight, `line-height: 1.65`, max measure ~38rem on the Entry page so 20-year-old prose stays comfortable to read.
- **UI chrome (nav, buttons, chips, metadata):** a humanist sans — e.g. **Inter** — kept deliberately distinct from the two serifs so the UI shell never gets confused with archival content.
- **Scale:** modular scale base 16px, ratio 1.25 (`12.8 / 16 / 20 / 25 / 31.25 / 39px` roughly, rounded to clean integers in implementation).

### 7.4 Component library decisions

- No heavy general-purpose component library (no MUI/Ant) — the scrapbook aesthetic is too custom for a generic design system to skin convincingly. Build a small bespoke component set (`PolaroidThumb`, `YearDrawer`, `TagChip`, `TimelineCard`, `PhotoLightbox`) styled with plain CSS (CSS Modules or vanilla CSS with custom properties — not Tailwind, since Tailwind's utility classes fight against the bespoke, texture-heavy aesthetic here more than they help).
- Icons: a single small hand-picked SVG icon set (e.g. Lucide, used sparingly) for functional chrome (search, edit-pencil, drawer chevrons) — never for decorative purposes; decoration comes from the polaroid/parchment treatment, not iconography.
- Motion: CSS transitions only (no animation library) — drawer expand/collapse, lightbox fade, card hover lift (`transform: translateY(-2px)` + shadow increase). All durations 150–250ms, all respecting `prefers-reduced-motion: reduce` (disable non-essential transitions entirely, keep instant state changes).

### 7.5 Responsive behavior

Single-PC target, but the window is resizable, so the layout uses fluid breakpoints rather than fixed device-class breakpoints:

| Width | Behavior |
|---|---|
| ≥1400px | TOC cabinet shows 5–6 polaroids per expanded drawer row; Timeline cards at full two-column alternating layout |
| 1000–1399px | 3–4 polaroids per row; Timeline cards remain alternating but narrower |
| 700–999px | 2 polaroids per row; Timeline collapses to single-column cards (photo on top, text below) |
| <700px | Single column throughout; facet sidebar on Search collapses to a slide-over drawer triggered by a filter icon (the app is not optimized for phone-width use, but should not break if the window is narrowed) |

### 7.6 Accessibility baseline

- Color contrast: all text/background pairs meet WCAG AA (4.5:1 body text, 3:1 large text) — every token in §7.2 is run through the actual WCAG 2.1 relative-luminance contrast formula against `--parchment-base` (not just eyeballed). Re-run this check (a ~15-line script) any time a token's hex value changes.
- All interactive elements reachable via keyboard (§6.8); visible focus ring (`outline: 2px solid var(--accent-green); outline-offset: 2px`) on every focusable element, never `outline: none` without a replacement.
- All images carry `alt` text sourced from the original `<img alt>`/figcaption when present; when absent, `alt="Photo from {entry title}, {event_date}"` as a non-empty fallback (never `alt=""` for content images — these are content, not decoration).
- `prefers-reduced-motion` and `prefers-contrast: more` are both honored (the latter swaps to a higher-contrast palette variant: darker ink, higher-contrast chip borders).
- Semantic HTML throughout (`<nav>`, `<main>`, `<article>` per entry, `<h1>`/`<h2>` hierarchy maintained even though visual design is non-default) so the app is screen-reader navigable, not just visually pretty.

---

## 8. Curation Mode Spec

> ❌ **Not built.** No in-app editing of titles, dates, tags, covers, or media
> order exists, and there is no review queue. The one curation need that proved
> real in practice — assigning each post to a book chapter — is met by editing
> the `CURATED` map in `scripts/assign_topics.py` and re-running it (§0.4). The
> API retains only `PATCH /api/entries/{id}/flag`. Everything below remains a
> valid design for a future v2.

### 8.1 Entry edit flows

Curate mode is a toggle (top-right switch, persisted in `localStorage`) that adds edit affordances to existing views rather than a separate editor page, so curation happens in-context:

- **Title:** click the title on an Entry page (Curate on) → inline `<input>` replaces the `<h1>` text, `Enter`/blur saves via `PATCH /api/entries/{id}` (`{"title": "..."}`), `Esc` cancels. Saving sets `title_locked_by_user=true` (§2.6) — a small lock icon appears next to the title afterward, with a tooltip "won't be overwritten by future syncs," and a "revert to source" affordance that clears the lock and restores `source_title`.
- **Date:** click the date chip → opens a date picker (native `<input type="date">` for simplicity, no custom calendar widget needed at this scale) → `PATCH` `{"event_date": "..."}`, same locking behavior. **`[NEEDS HUMAN DECISION]`** — the schema only supports a single exact `YYYY-MM-DD` date, with no way to mark a date as approximate/uncertain. Across ~1,700 posts spanning 20 years this is plausible to matter for at least a few old entries where Brian genuinely isn't sure of the exact day (though WordPress's own `published_time`/permalink date is always *some* exact date, so this only matters if Brian wants to *correct* one he knows is wrong without knowing the right answer either). Two options: **(A)** ship v1 as exact-date-only (simplest — the permalink-derived date is "true enough" even when uncertain, and Brian can always type his best guess into the date picker like any other field); **(B)** add an `event_date_is_approximate BOOLEAN DEFAULT 0` column now and a small "~" indicator in the UI when set, so uncertain dates are visibly flagged rather than silently presented as exact. Tradeoff: (A) is zero extra schema/UI work and is probably fine in practice since the underlying data already has real dates; (B) is a small addition (one column, one UI affordance) that adds honesty for the rare uncertain case but is speculative scope until Brian actually hits one. **Recommendation if forced to pick now: (A)** — defer (B) to a future migration if it turns out to matter once Brian is actually curating the real archive.
- **Tags:** the tag-chip row gets a `+` affordance → opens a combobox (type-ahead against `GET /api/tags`, creates a new tag on Enter if no match) → `POST /api/entries/{id}/tags`. Each chip gets an `×` on hover (Curate on only) → `DELETE /api/entries/{id}/tags/{tag_id}`. Auto-applied tags (`source='auto'`) are visually identical but show "(auto)" in their tooltip. Removing an auto-applied tag is itself a manual action and is not re-added unless `reindex --tags` runs again — there is no per-tag "never auto-apply to this entry" suppression table in v1; this keeps the behavior simple, with a suppression table available as a future addition if it proves necessary.
- **Cover image:** in the photo strip, hover any image (Curate on) → a small star/cover icon appears → click → `POST /api/entries/{id}/cover`.
- **Media reorder:** drag-and-drop within the photo strip (HTML5 drag events, or a lightweight library like `@dnd-kit` if drag-and-drop polish warrants a dependency) → on drop, `POST /api/entries/{id}/media/reorder` with the full new order.
- **Location:** the tag-chip row's `+` affordance (above) includes a "📍 Add location" option alongside "add tag"; selecting it opens a location combobox backed by `GET /api/locations` (type-ahead against already-known locations first, e.g. typing "malta" suggests the existing `Malta` row if Brian already tagged a prior entry) with a "create new location" fallback that asks for a free-text name and triggers a one-time best-effort geocode lookup via Nominatim (cached on the `Location` row, editable/correctable afterward since automated geocoding of informal place names will sometimes be wrong) → `POST /api/entries/{id}/locations` `{"location_id": N}` (mirrors the tag add/remove pair: `POST /api/entries/{id}/locations` / `DELETE /api/entries/{id}/locations/{location_id}`). This is the mechanism that lets Brian start tagging entries with `Location` rows ahead of Map v2 landing (§6.5).

### 8.2 Bulk tagging UX

A dedicated **Bulk Tag** panel, reached from Search results or the TOC: select entries via checkboxes (a "select all N results" affordance appears after any selection, matching the common "select all on page" + "select all matching filter" pattern), then a tag-picker applies/removes a tag across the whole selection in one action — `POST /api/entries/bulk-tag` `{"entry_ids": [...], "tag_id": N, "action": "add"|"remove"}` (one new bulk endpoint, otherwise unspecified elsewhere in §5, added here since bulk tagging is explicitly in scope per the task list). This is the primary tool for, e.g., selecting every 2026 Turkey-related entry that the keyword dictionary missed and applying `place:Turkey` in one pass.

### 8.3 Review Queue

A dedicated screen (`/curate/review`) listing entries by `review_status`:

- **`pending`** (newly ingested, never reviewed): card shows title/date/cover/auto-tags with an **Approve** button (`POST /api/entries/{id}/review {"action":"approve"}` → sets `review_status='reviewed'`) and a **Skip** (leave pending, revisit later) — approving is a lightweight acknowledgment, not a heavyweight edit requirement; Brian can approve in bulk without opening every entry, and only dive into Curate edits for entries that need it.
- **`possible_duplicate`**: card shows the entry side-by-side with `possible_duplicate_of`'s entry (title/date/first photo for each) and two actions: **Merge** (`{"action":"merge_into","target_entry_id":N}` — moves all `EntryMedia`/`EntryTag` from the source entry onto the target, marks the source `status` as a new value `merged` pointing at the target, target's `updated_at` advances) and **Not a duplicate** (`{"action":"dismiss_duplicate_flag"}` → `review_status='reviewed'`, clears `possible_duplicate_of`).
- **`source_changed_under_edit`**: card shows a diff view (locked field's current value vs. the newly-seen source value) with **Keep mine** (dismiss, no change) and **Accept source version** (clears the lock for that field, applies the source value).

### 8.4 Conflict resolution UI (resync changes existing content)

This is the same mechanism as `source_changed_under_edit` above, generalized: any resync that finds a source-side change to a field the user has locked does not silently apply or silently discard it — it always produces a queued, visible decision. The Entry page itself also shows a small "synced version available" banner inline (not only in the Review Queue) so the conflict is discoverable from the normal browsing flow, not just the dedicated queue.

---

## 9. Export / Vault Bundle

> ℹ️ **Two export formats now exist.** `--format bundle` (this section) is the
> zipped preservation artefact. `--format static-book` (§0.2) is the one used in
> practice: a plain folder that opens by double-clicking `index.html` — no
> server, no install, no internet — and refreshes incrementally in seconds.
> The static book, not the bundle, is what gets handed to family or copied to a
> USB stick.

### 9.1 Bundle directory structure

```text
vault-20260620-140500/
  manifest.json
  checksums.sha256
  db/
    scrapbook.sqlite              # full copy of the metadata DB at export time
  media/
    {sha256[0:2]}/{sha256[2:4]}/{sha256}.{ext}   # same content-addressed layout as the live store
  raw/                              # omitted entirely if --no-raw-snapshots
    grothadventures/2026/05/27-our-cows-horses/response.html
    ...
  index/
    entries.json                    # flat denormalized export of every entry + its media/tags, for any future static-viewer or migration tooling
    README.txt                      # human-readable: what this is, how to open it, when it was made
```

### 9.2 Manifest schema

```json
{
  "bundle_format_version": 1,
  "created_at": "2026-06-20T14:05:00Z",
  "source_app_version": "0.1.0",
  "scope": { "collection": null, "since": null, "includes_raw_snapshots": true },
  "counts": { "entries": 1698, "media": 10944, "total_bytes": 26108862464 },
  "schema": { "alembic_revision": "0001_initial_schema" },
  "checksum_manifest": "checksums.sha256",
  "signature": null
}
```
Per `ARCHITECTURE.md`'s "Optional signed manifest for long-term authenticity," the `signature` field is reserved (always `null` in v1) rather than omitted, so that adding real signing later (e.g. GPG-detached-signature or `age`-signing the manifest, with the signature embedded here or as a sibling `manifest.json.sig` file referenced from this field) is an additive change, not a bundle-format migration. **No signing is implemented in v1** — flagged as a still-open decision in §11 for whether it's wanted at all, since for a personal single-user archive the threat model (tampering detection across years of cold storage) is real but not urgent.

### 9.3 Checksums & integrity

`checksums.sha256` is a standard `sha256sum`-format file (`{hash}  {relative_path}`) covering every file in the bundle except itself and `manifest.json` (which is covered by a separate `manifest.json.sha256` sidecar so the manifest can be checksum-verified independently). `scrapbook export` runs a full verification pass immediately after writing the bundle (re-hash every copied file, compare to the `media.sha256` already known for media files, compute-and-store for raw snapshots/db copy) before declaring success — a bundle is never left in a "looks done but unverified" state. A standalone `scrapbook verify-bundle PATH` command (re-uses the same verification routine) lets Brian re-check a bundle on the backup drive months later without needing the original live database.

### 9.4 Self-contained browsing: server required, with a documented static fallback path

**v1 decision:** the vault bundle is browsed by pointing a running `scrapbook serve --data-dir <bundle>/db/..` (or a dedicated `scrapbook open-bundle PATH` convenience command) at the bundle — i.e., it reuses the same local FastAPI app, just against the bundle's copy of the DB/media instead of the live `data/` directory. This is **not** pure static HTML in v1, because the FTS5 search and dynamic filtering genuinely need a query engine, and reimplementing that as static pre-rendered pages is significant extra work for marginal benefit when the "server" here is a one-command localhost process, not real infrastructure.

**Documented fallback (lower priority, captured here so it's a known option, not an oversight):** `index/entries.json` plus the flat `media/` tree are sufficient raw material for a future "static mode" — a build step that pre-renders every Entry page to static HTML and ships a client-side JS search index (e.g. lunr.js) instead of FTS5/SQLite — if a truly server-less, double-click-an-HTML-file experience is ever required (e.g. handing the archive to a non-technical family member without Python installed). This is deferred indefinitely for v1; revisit only if that need actually arises.

### 9.5 Backup workflow integration

Per `ARCHITECTURE.md`'s operations workflow: `scrapbook export --format bundle` → copy the resulting directory to an external drive and/or cloud backup target (rclone/Backblaze/OneDrive — whatever Brian already uses; out of scope to build, the bundle is just a directory any backup tool can pick up). Because bundles are timestamped and immutable once verified, a sensible retention policy is "keep the last 2–3 verified bundles, prune older ones" — `scrapbook export --prune-older-than N` is a nice-to-have, not required for v1 (manual deletion is fine at this volume/cadence).

---

## 10. Phased Build Plan

> ✅ **Phases 0–1 and most of 3 shipped; Phase 2 (curation) did not.** The one
> task not fully satisfied is **1.1** — discovery skips the archive-index walk
> whenever the sitemap returns anything, so the "~1,698 posts back to 2004/12"
> acceptance criterion was never met (999 posts from 2013 were ingested instead).
> See §0.3. Phase 3 shipped far beyond its brief: the styling pass became the
> book redesign, and an unplanned static-book export (§0.2) was added.

Each task below is sized to be a single focused Claude Code session (roughly: one coherent unit of code + tests, reviewable in one sitting). Dependencies are listed explicitly; tasks within a week with no listed dependency on each other can be done in any order or in parallel by separate sessions.

### Phase 0 — Foundation (Week 1)

| # | Task | Depends on | Deliverable |
|---|---|---|---|
| 0.1 | Scaffold monorepo (`core/`, `app/`, `data/`, `config/`, `scripts/`) with `pyproject.toml`, `vite` app skeleton, `.gitignore` for `data/` | — | Repo builds; `core` importable; `app` runs `npm run dev` showing a placeholder page |
| 0.2 | Write `0001_initial_schema` Alembic migration from §3.3–3.4 verbatim | 0.1 | `alembic upgrade head` against a fresh SQLite file creates every table, index, FTS5 table, and trigger; a unit test inserts a row and confirms an FTS match round-trips |
| 0.3 | Implement `scrapbook init` and `scrapbook status` (status against an empty DB shows zeros, no crash) | 0.2 | `scrapbook init && scrapbook status` runs clean on a fresh checkout |
| 0.4 | Stand up FastAPI app skeleton bound to `127.0.0.1:8420`, `/api/stats` returning real zeros from the empty DB, `/healthz` | 0.2 | `curl localhost:8420/api/stats` returns valid JSON |
| 0.5 | Spike: verify whether `public-api.wordpress.com/rest/v1.1/sites/grothadventures.com/posts/` and/or `grothadventures.com/wp-json/wp/v2/posts` return usable JSON via a real HTTP client (`curl`/`httpie`, not a markdown-extracting fetch tool). This is a **time-boxed (≤30 min), purely optional optimization check**, not a gate: reconnaissance already conclusively proved the HTML-mode path works end-to-end (full content visible in fetched pages, sitemap parses, permalinks resolve), so Phase 1 proceeds on `api_mode=html` regardless of this spike's outcome. If the API does turn out to work, note it in `docs/api_spike_result.md` and pick it up opportunistically in task 1.3; if not (or if skipped for time), nothing in Phase 1 is blocked. | — | Either a short written finding committed to `docs/api_spike_result.md`, or explicitly skipped with a one-line note why — neither outcome blocks anything below |

**Definition of Done — Phase 0:** A developer can clone the repo, run `scrapbook init`, see a healthy empty DB via `scrapbook status`, and start the API and frontend dev servers. No ingestion code exists yet — that's intentional. Phase 0 does not need to know definitively which ingestion mode to use before Phase 1 starts, since HTML-mode is already proven viable by this PRD's reconnaissance (§2.1).

### Phase 1 — Ingest + browse MVP (Weeks 2–3)

| # | Task | Depends on | Deliverable |
|---|---|---|---|
| 1.1 | Implement Stage 0 discovery: robots.txt parse, sitemap.xml parse, archive-index walk (back to 2004/12) | 0.1–0.4 | Given the live site, discovery produces a candidate URL list whose count is within a few percent of the ~1,698 reference figure (§2.7); unit tests run against saved HTML/XML fixtures (capture today's robots.txt/sitemap.xml/one archive page as test fixtures during this task) |
| 1.2 | Implement Stage 2 HTML-mode extraction (title/body/date/images/video-refs) against saved fixture pages, including the `entry-content` selector spike mentioned in §2.3 | 1.1 | Extraction unit tests pass against ≥10 saved real post fixtures spanning different years/themes-eras (WordPress.com may have changed templates over 20 years — sample at least one fixture per ~5-year band) |
| 1.3 | (If 0.5 found the API viable) Implement Stage 2 API-mode extraction as an alternate path behind `api_mode` | 0.5, 1.2 | Same extraction-correctness tests pass via API-mode fixtures; if 0.5 found the API non-viable, this task is dropped and `html` is the only mode |
| 1.4 | Implement Stage 3 media download + sha256 dedup + content-addressed storage + EXIF/dimension extraction | 1.2 | Given a fixture post's image URLs, media lands at the correct `data/media/{prefix}/{prefix}/{sha256}.ext` path, `Media` rows are correct, rerunning produces zero new files (dedup proven) |
| 1.5 | Implement Stage 4 upsert + idempotency keying (§2.6) + auto-tagging (§2.8, seed `tag_keywords.yaml` from reconnaissance-sampled titles) | 1.2, 1.4 | Running the same fixture set twice produces zero duplicate `Entry` rows; date tags and at least the seeded place tags (Turkey, Malta, Tenerife, Dublin) apply correctly |
| 1.6 | Wire `scrapbook sync` end-to-end against the **live** site with `--max-posts 20` first, then a full `--full` backfill run | 1.1–1.5 | A real, complete sync of all ~1,698 posts completes; `scrapbook status` reports counts matching §2.7 expectations within tolerance; error taxonomy (§2.4) verified by checking the run's error log contains zero unclassified exceptions |
| 1.7 | Implement `GET /api/entries`, `GET /api/entries/{id}`, `GET /api/media/{sha256}/full`+`/thumb` | 0.4, 1.6 | API serves real synced data; an `<img>` pointed at `/api/media/.../full` renders in a browser with zero network requests beyond localhost |
| 1.8 | Build Home/TOC (year drawers) and Entry page (basic, unstyled-but-functional) in React | 1.7 | Clicking through Year → Entry → photo works end-to-end against the real synced archive |
| 1.9 | Implement FTS5-backed `/api/search` + basic Search page | 1.6, 1.7 | Searching "Malta" returns the Malta posts with highlighted snippets |

**Definition of Done — Phase 1:** Brian can run one command, ingest the entire real site, and click through Year → Entry → photo → Search entirely offline (network can be disconnected after sync completes and the app still works) — this is the `ARCHITECTURE.md` v1 Definition of Done's ingestion+browse half, testably true, not aspirational.

### Phase 2 — Curation + quality (Week 4)

| # | Task | Depends on | Deliverable |
|---|---|---|---|
| 2.1 | Implement `PATCH /api/entries/{id}` with field-locking semantics (§2.6, §5.2) | 1.7 | Editing title via API sets `title_locked_by_user`; a subsequent `scrapbook sync` against a fixture with a changed source title does **not** overwrite the locked title, and flags `source_changed_under_edit` instead |
| 2.2 | Implement tag add/remove, cover-select, media-reorder endpoints + their Curate-mode UI affordances (§8.1) | 2.1, 1.8 | Brian can retitle, retag, re-cover, and reorder photos on a real entry through the UI and have it persist across an app restart |
| 2.3 | Implement Review Queue screen + endpoints (`pending`/`possible_duplicate`/`source_changed_under_edit` flows, §8.3) | 2.1 | After a real sync, the Review Queue lists all newly-ingested entries; Approve/Merge/Keep-mine/Accept-source actions all work against real data |
| 2.4 | Implement the fallback-key possible-duplicate detector (§2.6) and bulk-tag endpoint/UI (§8.2) | 2.3 | A deliberately-duplicated fixture entry gets flagged; bulk-tagging 10 selected Search results applies a tag to all 10 |
| 2.5 | Improve dedupe/conflict edge cases found during the real Phase 1.6 full backfill (e.g., any `parse_error` entries surfaced) + write the import diagnostics report (`scrapbook status --json` consumed by a short Markdown report generator, or simply rely on `scrapbook status`'s existing output — decide based on whether Phase 1's `status` output already satisfies "import diagnostics," likely yes) | 1.6 | Zero entries remain in `parse_error` status after fixes (or each remaining one has a documented reason in the Review Queue) |
| 2.6 | Implement `scrapbook export --format bundle` (§4.6, §9.1–9.3): bundle directory assembly, `manifest.json`/`checksums.sha256` generation, post-write verification pass | 1.6, 2.1–2.4 (export should reflect curated, not just raw-synced, data) | Running `scrapbook export` against the real archive produces a bundle matching the §9.1 directory structure; `scrapbook verify-bundle` (2.7) on it reports zero mismatches |
| 2.7 | Implement `scrapbook verify-bundle` and `scrapbook open-bundle` (§4.8–4.9) | 2.6 | A bundle copied to a second location still opens and browses correctly via `scrapbook open-bundle`; deliberately corrupting one file in a copy makes `verify-bundle` report exactly that file, not a generic failure |
| 2.8 | Per `ARCHITECTURE.md`'s "Automate with one script: `scripts/monthly_update.(ps1\|sh)`," write `scripts/monthly_update.ps1` (primary — Brian's machine is Windows, per the project's own file paths) and `scripts/monthly_update.sh` (secondary, for portability): run `scrapbook sync`, then `scrapbook status --json` to check `review_queue.pending` and `posts_error` counts, print a clear human-readable summary (and exit non-zero if errors occurred, so the script is also cron/Task-Scheduler-friendly later even though v1 only requires manual double-click invocation), then `scrapbook export --format bundle`, then print a final reminder line telling Brian to copy the new bundle to his backup target (the script does **not** perform the actual offsite copy — §9.5 keeps that manual/external by design) | 2.6 | Double-clicking `monthly_update.ps1` on Brian's machine runs the full sync→status→export sequence unattended and ends with a one-screen human-readable summary, no errors |

**Definition of Done — Phase 2:** Brian can fully curate the real archive — fix any wrong auto-tag, merge any duplicate, clear the review queue to zero pending — using only the UI, no direct DB edits; and the full `sync → review → export → backup-reminder` operating routine from `ARCHITECTURE.md` runs end-to-end via a single script.

### Phase 3 — Scrapbook polish (Week 5)

| # | Task | Depends on | Deliverable |
|---|---|---|---|
| 3.1 | Implement the full visual design system (§7): parchment background, typography, color tokens, polaroid/cabinet components, self-hosted fonts | 1.8 | Visual QA against §7 spec; Lighthouse/axe accessibility check passes the §7.6 baseline |
| 3.2 | Build Timeline view (§6.2) with sticky year/month rail and infinite scroll | 1.7, 3.1 | Scrolling the full 1,698-entry timeline stays smooth (virtualized list, not 1,698 DOM nodes at once) |
| 3.3 | Build `PhotoLightbox` slideshow (§6.9) with filmstrip, preloading, keyboard nav | 1.8, 3.1 | Opening a 16-photo post (e.g. "Turkey, May 2026") and arrow-keying through all 16 feels instant after the first photo loads |
| 3.4 | Implement full keyboard navigation spec (§6.8) across all views | 3.2, 3.3 | Manual keyboard-only QA pass covers every row of the §6.8 table |
| 3.5 | Implement the offline self-check (§6.10) as an automated build-time test | 3.1–3.4 | CI (or a local `npm run check:offline`) fails the build if any non-localhost asset reference is found |

**Definition of Done — Phase 3:** The app looks and feels like a designed product, not a CRUD scaffold, every view matches §6/§7, and the offline guarantee is enforced by an automated check rather than a promise.

### Phase 4 — Additional sources (later, not yet scheduled)

| # | Task | Depends on | Deliverable |
|---|---|---|---|
| 4.1 | Design the `photo_library` connector interface (Google Photos export / Apple Photos export) against the existing `Source`/`IngestRun`/`Entry`/`Media` schema — confirm no schema changes needed, or scope the ones that are | Phase 1–3 complete | A short design doc; schema migration if required |
| 4.2 | Implement scanned-album ingestion pipeline (manual folder scan → `Entry` per album/page) | 4.1 | A test folder of scanned images imports as entries with media |
| 4.3 | Map view v2 (§6.5): geocode existing `Location` rows via Nominatim, build the Leaflet/MapLibre map, pin clustering | Phase 1–3 complete | Map tab shows pins for every geocoded entry, clicking filters the entry list |

**Definition of Done — Phase 4:** Out of scope for the current build cycle; this section exists so future work has a clear, schema-compatible starting point rather than a redesign.

---

## 11. Open Questions & Decisions Needed

> **Resolved during the build (July 2026):**
> - **(1) Media volume** — answered by measurement, and it came in *far* under
>   the 20–35 GB estimate: **3,077 photos, ~11.5 GB total archive** including raw
>   HTML snapshots. No change to backup strategy needed; raw snapshots stay on.
> - **(4) Theme/markup drift** — real, and it bit exactly as predicted. Posts
>   from 2013–2015 carry Windows Live Writer embeds pointing at dead SkyDrive
>   albums; handled in the frontend by DOM-based prose cleanup (§0.6), not by the
>   extractor.
> - **(5) Rate-limiting** — never triggered. A full 999-post backfill at
>   1.5–3s/request completed with `errors: 0`.
> - **Still open:** (2) comments, (3) offline map tiles, (6) signed manifest,
>   (7) AI-edited image detection — all untouched, all still valid as written.
>
> **New open question — the biggest one:** whether to close the pre-2013
> ingestion gap (§0.3). Doing so means implementing the archive walk that task
> 1.1 originally called for, then a multi-hour backfill of 600+ posts and their
> photos. Until then the book is "the blog since August 2013", not the whole
> blog.

These require a human decision (Brian's) before or during implementation; none of them block starting Phase 0, but several block specific later tasks as noted.

1. **Media volume estimate is a sampled extrapolation, not a measurement.** §2.7's 20–35 GB estimate is built from a handful of sampled posts' photo counts. **Decision needed:** none yet — Phase 1 task 1.6's real full backfill will produce the true number; if it's wildly larger than estimated (e.g. >100 GB), Brian should be informed before committing to a backup/storage plan, since that changes export bundle handling (§9) and possibly argues for `--no-raw-snapshots` exports as the default rather than the exception.
2. **Comment ingestion.** The source blog has visible comment counts/threads on posts; reconnaissance found these counts are mostly small in sampled posts (typically "Leave a comment"/0, occasionally 1–2; no large threads observed), so if comments are ever ingested the realistic volume is likely modest (low thousands across ~1,700 posts). **Decision needed:** confirm comments stay out of scope for v1 (current assumption) or should be pulled into a future-phase task now so the schema accounts for it (a `comment` table referencing `entry_id` would be the natural addition).
3. **Offline map tiles.** Deferred to Phase 4 — caching OSM tiles locally for true offline map browsing is consistent with the offline-first principle but adds real storage/complexity (tile caching at a useful zoom range for the countries visited is itself a non-trivial amount of data). **Recommendation for Phase 4 task 4.3:** ship Map v2 with online tiles first (a known, scoped exception to offline-first, since the map is already a v2/Phase-4 feature, not v1) and revisit offline tile caching only if it's missed in practice.
4. **Risk — site theme/markup drift over 20 years.** WordPress.com has very likely changed this blog's underlying theme/template multiple times since December 2004. Mitigated by §2.3's extraction strategy, which tries known WordPress core content-container classes first, then falls back to a structural extraction bounded by stable text landmarks ("Share this:", "Like Loading", "*Related*", the comment form) observed on every sampled page regardless of theme. Phase 1 task 1.2's "one fixture per ~5-year band" requirement is the verification step that proves this fallback actually works across eras and must not be skipped.
5. **Risk — WordPress.com rate-limiting or blocking the crawler.** `robots.txt` suggests bulk crawlers use "the firehose" instead of regular crawling (§2.1) — a courtesy note aimed at large-scale crawlers, not a restriction on a personal archive tool fetching one's own ~1,700-post blog at a self-imposed 1.5–3s/request pace, but WordPress.com could in principle rate-limit or challenge (CAPTCHA) an automated client if it ever misbehaves. Mitigated by conservative politeness defaults (§2.2), exponential backoff (§2.4), and an early-abort-on-repeated-failure safeguard so the connector fails loudly rather than hammering a block wall for hours.
6. **Signed manifest.** Per `ARCHITECTURE.md`'s "Optional signed manifest for long-term authenticity" — is cryptographic signing of the export manifest actually wanted for v1, given the single-user/personal-archive threat model? Current default: no, `signature` field reserved as `null` (§9.2). **Decision needed only if Brian's risk tolerance differs from this default.**
7. **AI-edited image auto-detection.** `Media.derived_from_media_id` (nullable self-reference, §3.3) exists in the v1 schema, but is **not auto-populated** by the connector (no filename/temporal-proximity heuristic is built) — it's purely a Curate-mode-settable field for now. **Decision needed:** whether to build automatic detection later; low-priority, no impact on v1 if left manual-only.

---

