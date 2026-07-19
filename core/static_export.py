"""Static-book exporter: writes the whole book into a plain folder that works
by double-clicking index.html — no server, no install, safe to hand to a
friend on a USB stick.

Layout of the output folder:
    index.html            the entire app (single self-contained file)
    favicon.svg
    book-data/boot.js     flags static mode + embeds the table of contents
    book-data/search.js   text index for in-browser search
    book-data/entries/<id>.js   one file per story, loaded on demand
    media/<sha256>.<ext>  every photo, flat, content-hash named

Re-running the export into the same folder is incremental for photos: a
photo's filename is its content hash, so files that already exist are
skipped. Data files are tiny and always rewritten.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from core.api.routers.book import build_toc
from core.api.routers.entries import _entry_dict
from core.db.models import Entry


def _js(payload: object) -> str:
    """JSON as an ASCII-safe JS literal (safe for any file encoding)."""
    return json.dumps(payload, ensure_ascii=True)


def _relativize(text: str) -> str:
    """Rewrite served-mode media URLs to folder-relative ones."""
    return text.replace("/api/media/", "media/")


def export_static_book(db: Session, cfg, dist_dir: Path, out_dir: Path) -> dict:
    """Write the static book to out_dir. Returns summary stats."""
    index_src = dist_dir / "index.html"
    if not index_src.exists():
        raise FileNotFoundError(
            "app/dist/index.html not found — build the app once with: cd app && npm run build"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "book-data" / "entries").mkdir(parents=True, exist_ok=True)
    (out_dir / "media").mkdir(exist_ok=True)

    # ── index.html: copy and inject the boot script.
    # A classic script in <head> always runs before the app's module script.
    html = index_src.read_text(encoding="utf-8")
    boot_tag = '<script src="book-data/boot.js"></script>'
    if boot_tag not in html:
        if "</head>" not in html:
            raise RuntimeError("Unexpected index.html: no </head> tag to inject into")
        html = html.replace("</head>", f"  {boot_tag}\n  </head>", 1)
    (out_dir / "index.html").write_text(html, encoding="utf-8")

    favicon = dist_dir / "favicon.svg"
    if favicon.exists():
        shutil.copyfile(favicon, out_dir / "favicon.svg")

    # ── Table of contents → boot.js
    toc = build_toc(db)
    boot = (
        "window.__BOOK_STATIC__=true;\n"
        "window.__BOOK_ENTRIES__={};\n"
        f"window.__BOOK_TOC__={_relativize(_js(toc))};\n"
    )
    (out_dir / "book-data" / "boot.js").write_text(boot, encoding="utf-8")

    # ── One data file per entry
    entries = db.query(Entry).all()
    for e in entries:
        payload = _entry_dict(e, include_html=True)
        js = (
            "window.__BOOK_ENTRIES__=window.__BOOK_ENTRIES__||{};\n"
            f"window.__BOOK_ENTRIES__[{e.id}]={_relativize(_js(payload))};\n"
        )
        (out_dir / "book-data" / "entries" / f"{e.id}.js").write_text(js, encoding="utf-8")

    # ── Search index
    search_index = [
        {
            "id": e.id,
            "title": e.title,
            "event_date": e.event_date,
            "text": (e.text_content or e.summary or "")[:20000],
        }
        for e in entries
    ]
    (out_dir / "book-data" / "search.js").write_text(
        f"window.__BOOK_SEARCH__={_js(search_index)};\n", encoding="utf-8"
    )

    # ── Photos: flat, content-hash named, skip ones already in place
    copied = 0
    skipped = 0
    missing = 0
    seen: set[str] = set()
    for e in entries:
        for em in e.media_items:
            m = em.media
            if not m or m.status != "downloaded":
                continue
            name = f"{m.sha256}.{m.ext}"
            if name in seen:
                continue
            seen.add(name)
            dst = out_dir / "media" / name
            if dst.exists():
                skipped += 1
                continue
            src = cfg.media_path(m.sha256, m.ext)
            if not src.exists():
                missing += 1
                continue
            shutil.copyfile(src, dst)
            copied += 1

    return {
        "entries": len(entries),
        "photos_copied": copied,
        "photos_already_there": skipped,
        "photos_missing": missing,
    }
