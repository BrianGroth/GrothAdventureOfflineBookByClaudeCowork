"""WordPress connector for syncing grothadventures.com."""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
import yaml
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from sqlalchemy.orm import Session

from core.config import AppConfig
from core.db.models import (
    Entry, EntryMedia, EntryTag, IngestRun, Media, RawSnapshot, Source, Tag
)

console = Console()

USER_AGENT = (
    "GrothAdventuresScrapbookBot/1.0 "
    "(+personal archive tool; operated by groth.brian@gmail.com; respects robots.txt)"
)

CONTENT_SELECTORS = [
    ".entry-content",
    ".post-content",
    ".post-entry",
    "article .entry",
    "article .content",
    ".hentry .content",
    "article",
    "main",
]

IMAGE_PARAM_STRIP = re.compile(r"[?&](w|h|resize|ssl|fit|crop|quality)=[^&]*")
PERMALINK_DATE_RE = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/([^/]+)/?$")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _clean_image_url(url: str) -> str:
    """Strip WordPress resize/CDN query params to get original image URL."""
    parsed = urlparse(url)
    # Remove query string params that are resize/display only
    if parsed.query:
        params = parsed.query.split("&")
        keep = [p for p in params if not re.match(r"^(w|h|resize|ssl|fit|crop|quality)=", p)]
        new_query = "&".join(keep)
        parsed = parsed._replace(query=new_query)
    return urlunparse(parsed)


def _extract_date_from_permalink(permalink: str) -> Optional[str]:
    """Extract event date from WordPress permalink pattern /YYYY/MM/DD/slug/."""
    m = PERMALINK_DATE_RE.search(permalink)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def _source_entry_id(permalink: str) -> str:
    """Compute stable entry ID from permalink."""
    path = urlparse(permalink).path.lower().rstrip("/")
    return _sha256_str(path)


def _html_to_text(html: str) -> str:
    """Extract plain text from HTML."""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator="\n", strip=True)


def _make_summary(text: str, max_chars: int = 280) -> str:
    """Make a short summary from plain text."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > max_chars // 2:
        cut = cut[:last_space]
    return cut + "…"


def _strip_wp_boilerplate(html_content: str) -> str:
    """Remove WordPress boilerplate sections (Share this, Related, Like Loading)."""
    if not html_content:
        return html_content
    soup = BeautifulSoup(html_content, "lxml")

    # Remove elements that contain boilerplate text markers
    BOILERPLATE_MARKERS = [
        "share this:",
        "like loading",
        "like this:",
        "related",
        "leave a comment",
        "leave a reply",
        "post navigation",
    ]

    # Remove known WP sharing/related widget classes
    WP_BOILERPLATE_CLASSES = [
        "sharedaddy", "sd-sharing", "jp-relatedposts", "wpl-likebox",
        "post-navigation", "entry-footer", "post-footer", "share-this",
        "wpcnt", "likes-widget", "post-likes-widget-placeholder",
    ]
    for cls in WP_BOILERPLATE_CLASSES:
        for el in soup.find_all(class_=lambda c: c and cls in c):
            el.decompose()

    # Walk the tree and remove any element whose text starts with a boilerplate marker
    for el in soup.find_all(["p", "div", "section", "aside", "nav", "h2", "h3", "h4", "ul"]):
        text = el.get_text(strip=True).lower()
        if any(text.startswith(m) for m in BOILERPLATE_MARKERS):
            # Remove this element and everything after it at the same level
            parent = el.parent
            if parent:
                siblings = list(el.next_siblings)
                el.decompose()
                for sib in siblings:
                    if hasattr(sib, 'decompose'):
                        sib.decompose()
            break

    # Return just the inner content (strip the outer wrapper tag lxml adds)
    body = soup.find("body")
    if body:
        return "".join(str(c) for c in body.children)
    return str(soup)


def apply_auto_tags(db: Session, entry: Entry, cfg: AppConfig) -> None:
    """Apply auto-generated tags to an entry based on date and keywords."""
    tags_to_apply: list[tuple[str, str, str]] = []  # (slug, label, category)

    # Date-based tags
    if entry.event_date:
        year = entry.event_date[:4]
        tags_to_apply.append((f"year-{year}", year, "year"))

        month = int(entry.event_date[5:7]) if len(entry.event_date) >= 7 else 0
        if month in (12, 1, 2):
            tags_to_apply.append(("season-winter", "Winter", "season"))
        elif month in (3, 4, 5):
            tags_to_apply.append(("season-spring", "Spring", "season"))
        elif month in (6, 7, 8):
            tags_to_apply.append(("season-summer", "Summer", "season"))
        elif month in (9, 10, 11):
            tags_to_apply.append(("season-fall", "Fall", "season"))

    # Keyword-based tags
    keywords_path = Path(__file__).parent.parent.parent / "config" / "tag_keywords.yaml"
    if keywords_path.exists():
        with open(keywords_path, "r", encoding="utf-8") as f:
            kw_config = yaml.safe_load(f) or {}
        keywords = kw_config.get("keywords", {})
        text_lower = (entry.title + " " + entry.text_content).lower()
        for tag_slug, kw_info in keywords.items():
            terms = kw_info.get("terms", [])
            label = kw_info.get("label", tag_slug)
            category = kw_info.get("category", "keyword")
            if any(term.lower() in text_lower for term in terms):
                tags_to_apply.append((tag_slug, label, category))

    # Ensure tags exist and link them
    for slug, label, category in tags_to_apply:
        tag = db.query(Tag).filter_by(slug=slug).first()
        if not tag:
            tag = Tag(slug=slug, label=label, category=category)
            db.add(tag)
            db.flush()

        existing = db.query(EntryTag).filter_by(
            entry_id=entry.id, tag_id=tag.id
        ).first()
        if not existing:
            db.add(EntryTag(entry_id=entry.id, tag_id=tag.id, auto=1))


class RateLimiter:
    """Token bucket rate limiter with min/max delays."""

    def __init__(self, min_delay: float = 1.5, max_delay: float = 3.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_request = 0.0

    async def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._last_request = time.monotonic()


class WordPressConnector:
    """Connector for syncing a WordPress blog to the local database."""

    def __init__(
        self,
        cfg: AppConfig,
        source_model: Source,
        source_config: dict[str, Any],
        ingest_run_id: Optional[int],
        dry_run: bool = False,
        verbose: bool = False,
        max_posts: Optional[int] = None,
        since: Optional[str] = None,
        no_media: bool = False,
        concurrency: int = 3,
    ):
        self.cfg = cfg
        self.source = source_model
        self.source_config = source_config
        self.ingest_run_id = ingest_run_id
        self.dry_run = dry_run
        self.verbose = verbose
        self.max_posts = max_posts
        self.since = since
        self.no_media = no_media
        self.concurrency = concurrency
        self.base_url = source_model.base_url or source_config.get("base_url", "")
        self.rate_limiter = RateLimiter(
            min_delay=source_config.get("rate_limit_min", 1.5),
            max_delay=source_config.get("rate_limit_max", 3.0),
        )
        self._consecutive_failures = 0
        self.stats: dict[str, int] = {
            "discovered": 0,
            "fetched": 0,
            "new": 0,
            "updated": 0,
            "skipped": 0,
            "media_downloaded": 0,
            "media_failed": 0,
            "errors": 0,
        }

    def _log(self, msg: str) -> None:
        if self.verbose:
            console.print(f"  [dim]{msg}[/dim]")

    async def _fetch(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        """Fetch a URL with rate limiting and error tracking."""
        await self.rate_limiter.wait()
        try:
            response = await client.get(url, follow_redirects=True, timeout=30.0, **kwargs)
            self._consecutive_failures = 0
            return response
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 3:
                raise RuntimeError(
                    f"3 consecutive connection failures. Last error: {e}. Aborting."
                ) from e
            raise

    async def _discover_posts(self, client: httpx.AsyncClient) -> list[str]:
        """Stage 0+1: Discover all post URLs via sitemap or archive walk."""
        urls: list[str] = []

        # Try sitemap.xml
        sitemap_url = urljoin(self.base_url, "/sitemap.xml")
        self._log(f"Checking sitemap: {sitemap_url}")

        try:
            resp = await self._fetch(client, sitemap_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml-xml")

                # Check for sitemap index
                sitemap_tags = soup.find_all("sitemap")
                if sitemap_tags:
                    # It's a sitemap index - find the post sitemap
                    for sm in sitemap_tags:
                        loc = sm.find("loc")
                        if loc and "post" in loc.text.lower():
                            post_sitemap_url = loc.text.strip()
                            self._log(f"Found post sitemap: {post_sitemap_url}")
                            try:
                                resp2 = await self._fetch(client, post_sitemap_url)
                                if resp2.status_code == 200:
                                    soup2 = BeautifulSoup(resp2.text, "lxml-xml")
                                    for loc_tag in soup2.find_all("loc"):
                                        u = loc_tag.text.strip()
                                        if self._is_post_url(u):
                                            urls.append(u)
                            except Exception as e:
                                self._log(f"Failed to fetch post sitemap: {e}")
                else:
                    # Single sitemap with <url> entries
                    for loc_tag in soup.find_all("loc"):
                        u = loc_tag.text.strip()
                        if self._is_post_url(u):
                            urls.append(u)
        except Exception as e:
            self._log(f"Sitemap fetch failed: {e}")

        if not urls:
            # Fallback: archive walk via WordPress archive pages
            self._log("Falling back to archive walk...")
            urls = await self._walk_archives(client)

        # Filter by date if --since provided
        if self.since:
            before = len(urls)
            urls = [u for u in urls if self._url_date_after(u, self.since)]
            self._log(f"Date filter ({self.since}): {before} -> {len(urls)} URLs")

        return urls

    def _is_post_url(self, url: str) -> bool:
        """Check if URL looks like a WordPress post (has /YYYY/MM/DD/ pattern)."""
        return bool(PERMALINK_DATE_RE.search(url))

    def _url_date_after(self, url: str, since: str) -> bool:
        """Check if a URL's date is on or after the given date."""
        date = _extract_date_from_permalink(url)
        if not date:
            return True  # Include undated posts
        return date >= since

    async def _walk_archives(self, client: httpx.AsyncClient) -> list[str]:
        """Walk WordPress monthly archive pages to collect post URLs."""
        urls: list[str] = []
        page = 1
        max_pages = 200

        while page <= max_pages:
            archive_url = f"{self.base_url.rstrip('/')}/?paged={page}" if page > 1 else self.base_url
            self._log(f"Archive page {page}: {archive_url}")
            try:
                resp = await self._fetch(client, archive_url)
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, "lxml")
                found = 0
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    full_url = urljoin(self.base_url, href)
                    if self._is_post_url(full_url) and full_url not in urls:
                        urls.append(full_url)
                        found += 1

                if found == 0:
                    break
                page += 1
            except RuntimeError:
                raise
            except Exception as e:
                self._log(f"Archive page {page} failed: {e}")
                break

        return urls

    async def _fetch_post(
        self, client: httpx.AsyncClient, url: str, db: Session
    ) -> Optional[dict[str, Any]]:
        """Stage 2: Fetch and parse a single post."""
        self._log(f"Fetching: {url}")
        try:
            resp = await self._fetch(client, url)
            if resp.status_code != 200:
                self._log(f"HTTP {resp.status_code} for {url}")
                self.stats["errors"] += 1
                return None
        except RuntimeError:
            raise
        except Exception as e:
            self._log(f"Fetch error for {url}: {e}")
            self.stats["errors"] += 1
            return None

        html = resp.text
        soup = BeautifulSoup(html, "lxml")

        # Extract title — og:title is always the post title on WordPress.com;
        # the page's first <h1> is often the site name in the banner, not the post.
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", "").strip()
        if not title:
            # Specific entry-title class before falling back to any h1
            title_tag = (
                soup.find(class_=lambda c: c and "entry-title" in c)
                or soup.find(class_=lambda c: c and "post-title" in c)
            )
            if title_tag:
                title = title_tag.get_text(strip=True)
        if not title:
            title = url.rstrip("/").split("/")[-1].replace("-", " ").title()

        # Extract content using priority selectors
        content_el = None
        for sel in CONTENT_SELECTORS:
            content_el = soup.select_one(sel)
            if content_el:
                break

        if not content_el:
            # Structural fallback: find largest text block
            candidates = soup.find_all(["div", "section"], class_=True)
            if candidates:
                content_el = max(candidates, key=lambda el: len(el.get_text()))
            else:
                content_el = soup.find("body")

        html_content = str(content_el) if content_el else ""
        html_content = _strip_wp_boilerplate(html_content)
        text_content = _html_to_text(html_content)

        # Extract images from content
        images: list[dict[str, Any]] = []
        if content_el:
            for img in content_el.find_all("img"):
                src = img.get("src", "")
                if not src or src.startswith("data:"):
                    continue
                src = urljoin(url, src)
                src = _clean_image_url(src)
                images.append({
                    "url": src,
                    "alt": img.get("alt", ""),
                    "caption": "",
                })

        # Look for WP gallery captions
        if content_el:
            for figure in content_el.find_all("figure"):
                img = figure.find("img")
                caption_el = figure.find("figcaption")
                if img and caption_el:
                    src = _clean_image_url(urljoin(url, img.get("src", "")))
                    for im in images:
                        if im["url"] == src:
                            im["caption"] = caption_el.get_text(strip=True)

        # Event date from permalink (preferred over meta tags)
        event_date = _extract_date_from_permalink(url)

        # Publish date from meta
        publish_date = None
        pub_meta = soup.find("meta", property="article:published_time")
        if pub_meta:
            publish_date = pub_meta.get("content", "")[:10]
        if not publish_date:
            time_tag = soup.find("time", attrs={"datetime": True})
            if time_tag:
                publish_date = time_tag["datetime"][:10]

        # Author
        author = None
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta:
            author = author_meta.get("content", "")
        if not author:
            author_el = soup.find(class_=lambda c: c and "author" in c)
            if author_el:
                author = author_el.get_text(strip=True)[:100]

        # Save raw snapshot
        source_entry_id = _source_entry_id(url)
        if not self.dry_run:
            self._save_raw_snapshot(db, source_entry_id, url, html, dict(resp.headers))

        return {
            "permalink": url,
            "source_entry_id": source_entry_id,
            "title": title,
            "event_date": event_date,
            "publish_date": publish_date,
            "author": author,
            "html_content": html_content,
            "text_content": text_content,
            "summary": _make_summary(text_content),
            "images": images,
        }

    def _save_raw_snapshot(
        self,
        db: Session,
        source_entry_id: str,
        url: str,
        html: str,
        headers: dict,
    ) -> None:
        """Save raw HTML snapshot to disk."""
        date = _extract_date_from_permalink(url) or "unknown"
        year = date[:4] if date != "unknown" else "unknown"
        month = date[5:7] if len(date) >= 7 else "00"
        slug = url.rstrip("/").split("/")[-1]
        day = date[8:10] if len(date) >= 10 else "00"

        snap_dir = self.cfg.raw_path(self.source.id, year, month, f"{day}-{slug}")
        snap_dir.mkdir(parents=True, exist_ok=True)

        html_path = snap_dir / "response.html"
        headers_path = snap_dir / "headers.json"

        html_path.write_text(html, encoding="utf-8")
        headers_path.write_text(json.dumps(dict(headers), indent=2), encoding="utf-8")

    async def _download_media(
        self,
        client: httpx.AsyncClient,
        db: Session,
        image_info: dict[str, Any],
        entry: Entry,
        position: int,
        semaphore: asyncio.Semaphore,
        linked_ids: set[int],
    ) -> Optional[Media]:
        """Stage 3: Download a single media file.

        linked_ids holds media ids already linked to this entry during this
        post's downloads. The session runs with autoflush=False, so a pending
        EntryMedia row is invisible to the guard query below — without this
        set, a post using the same photo twice would insert a duplicate
        (entry_id, media_id) link and blow up the commit.
        """
        async with semaphore:
            url = image_info["url"]
            if not url or not url.startswith("http"):
                return None

            await self.rate_limiter.wait()

            try:
                resp = await client.get(url, follow_redirects=True, timeout=60.0)
                if resp.status_code != 200:
                    self.stats["media_failed"] += 1
                    return None

                content = resp.content
                sha = _sha256(content)

                # Determine extension
                content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                ext_map = {
                    "image/jpeg": "jpg",
                    "image/png": "png",
                    "image/gif": "gif",
                    "image/webp": "webp",
                    "image/svg+xml": "svg",
                    "video/mp4": "mp4",
                    "video/quicktime": "mov",
                }
                ext = ext_map.get(content_type, "bin")
                # Also try URL extension
                url_path = urlparse(url).path
                if "." in url_path:
                    url_ext = url_path.rsplit(".", 1)[-1].lower().split("?")[0]
                    if url_ext in ["jpg", "jpeg", "png", "gif", "webp", "svg", "mp4", "mov"]:
                        ext = "jpg" if url_ext == "jpeg" else url_ext

                if self.dry_run:
                    self.stats["media_downloaded"] += 1
                    return None

                # Check if already downloaded
                existing = db.query(Media).filter_by(
                    source_id=self.source.id, sha256=sha
                ).first()

                if existing and existing.status == "downloaded":
                    # Just link it (once)
                    em = db.query(EntryMedia).filter_by(
                        entry_id=entry.id, media_id=existing.id
                    ).first()
                    if not em and existing.id not in linked_ids:
                        linked_ids.add(existing.id)
                        db.add(EntryMedia(
                            entry_id=entry.id,
                            media_id=existing.id,
                            position=position,
                            role="hero" if position == 0 else "inline",
                        ))
                    return existing

                # Save to disk
                dest = self.cfg.media_path(sha, ext)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)

                # Get image dimensions
                width = height = None
                try:
                    from PIL import Image
                    with Image.open(dest) as img:
                        width, height = img.size
                except Exception:
                    pass

                # Save EXIF
                exif_json = None
                if ext in ("jpg", "jpeg"):
                    try:
                        import exifread
                        tags = exifread.process_file(open(dest, "rb"), details=False)
                        if tags:
                            exif_json = json.dumps({k: str(v) for k, v in tags.items()})
                    except Exception:
                        pass

                media_obj = Media(
                    source_id=self.source.id,
                    original_url=url,
                    sha256=sha,
                    ext=ext,
                    mime_type=content_type,
                    width=width,
                    height=height,
                    file_size=len(content),
                    exif_json=exif_json,
                    alt_text=image_info.get("alt", ""),
                    caption=image_info.get("caption", ""),
                    status="downloaded",
                    created_at=_now_utc(),
                )
                db.add(media_obj)
                db.flush()

                if media_obj.id not in linked_ids:
                    linked_ids.add(media_obj.id)
                    db.add(EntryMedia(
                        entry_id=entry.id,
                        media_id=media_obj.id,
                        position=position,
                        role="hero" if position == 0 else "inline",
                    ))

                self.stats["media_downloaded"] += 1
                return media_obj

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._log(f"Media download failed for {url}: {e}")
                self.stats["media_failed"] += 1
                return None

    def _upsert_entry(self, db: Session, post_data: dict[str, Any]) -> tuple[Entry, bool]:
        """Stage 4: Upsert an entry into the database. Returns (entry, is_new)."""
        existing = db.query(Entry).filter_by(
            source_id=self.source.id,
            source_entry_id=post_data["source_entry_id"],
        ).first()

        now = _now_utc()

        if existing:
            existing.title = post_data["title"]
            existing.event_date = post_data["event_date"]
            existing.publish_date = post_data["publish_date"]
            existing.author = post_data["author"]
            existing.html_content = post_data["html_content"]
            existing.text_content = post_data["text_content"]
            existing.summary = post_data["summary"]
            existing.ingest_run_id = self.ingest_run_id
            existing.updated_at = now
            return existing, False
        else:
            entry = Entry(
                source_id=self.source.id,
                source_entry_id=post_data["source_entry_id"],
                permalink=post_data["permalink"],
                title=post_data["title"],
                event_date=post_data["event_date"],
                publish_date=post_data["publish_date"],
                author=post_data["author"],
                html_content=post_data["html_content"],
                text_content=post_data["text_content"],
                summary=post_data["summary"],
                ingest_run_id=self.ingest_run_id,
                created_at=now,
                updated_at=now,
            )
            db.add(entry)
            return entry, True

    async def run_sync(self, db: Session, full: bool = False) -> dict[str, int]:
        """Run the full sync pipeline."""
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(headers=headers) as client:
            # Stage 0+1: Discovery
            console.print("[bold]Stage 1:[/bold] Discovering posts...")
            all_urls = await self._discover_posts(client)

            if not full:
                # In incremental mode, skip already-synced entries
                known_ids = set(
                    row[0]
                    for row in db.query(Entry.source_entry_id)
                    .filter(Entry.source_id == self.source.id)
                    .all()
                )
                all_urls = [u for u in all_urls if _source_entry_id(u) not in known_ids]
                console.print(f"  [dim]{len(all_urls)} new posts to sync[/dim]")

            if self.max_posts:
                all_urls = all_urls[: self.max_posts]

            self.stats["discovered"] = len(all_urls)
            console.print(f"  Found [bold]{len(all_urls)}[/bold] posts to process")

            if not all_urls:
                return self.stats

            # Stage 2: Fetch posts
            console.print("[bold]Stage 2:[/bold] Fetching posts...")
            semaphore = asyncio.Semaphore(self.concurrency)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Fetching posts...", total=len(all_urls))

                for url in all_urls:
                    try:
                        post_data = await self._fetch_post(client, url, db)
                    except RuntimeError as e:
                        # Consecutive failure abort
                        console.print(f"[red]Aborting: {e}[/red]")
                        return self.stats

                    if post_data is None:
                        self.stats["skipped"] += 1
                        progress.advance(task)
                        continue

                    self.stats["fetched"] += 1

                    if not self.dry_run:
                        entry, is_new = self._upsert_entry(db, post_data)
                        db.flush()

                        if is_new:
                            self.stats["new"] += 1
                        else:
                            self.stats["updated"] += 1

                        # Stage 3: Download media
                        if not self.no_media and post_data["images"]:
                            # A post can reference the same image more than
                            # once — download and link each URL only once.
                            unique_images = []
                            seen_urls: set[str] = set()
                            for img in post_data["images"]:
                                u = img.get("url")
                                if u and u in seen_urls:
                                    continue
                                if u:
                                    seen_urls.add(u)
                                unique_images.append(img)

                            media_semaphore = asyncio.Semaphore(self.concurrency)
                            linked_ids: set[int] = set()
                            media_tasks = []
                            for i, img in enumerate(unique_images[:20]):  # max 20 images per post
                                media_tasks.append(
                                    self._download_media(client, db, img, entry, i, media_semaphore, linked_ids)
                                )

                            media_results = await asyncio.gather(*media_tasks, return_exceptions=True)

                            # Set hero image to first successfully downloaded image
                            hero = next(
                                (m for m in media_results if isinstance(m, Media) and m.id),
                                None,
                            )
                            if hero and not entry.hero_media_id:
                                entry.hero_media_id = hero.id

                        # Stage 4: Auto-tag
                        apply_auto_tags(db, entry, self.cfg)

                        try:
                            db.commit()
                        except Exception as e:
                            # One bad post must not kill a long sync: drop its
                            # pending changes, count it, move on. An
                            # incremental re-run will retry it.
                            db.rollback()
                            self._log(f"Commit failed for {url}: {e}")
                            self.stats["errors"] += 1

                    progress.advance(task)

        return self.stats
