"""Full-text search endpoints using FTS5."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.db.session import get_session
from core.db.models import Entry

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search_entries(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    year: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    db: Session = Depends(get_session),
):
    """Full-text search across entries using FTS5."""
    # Sanitize query for FTS5 (escape special characters)
    safe_q = q.replace('"', '""')

    try:
        fts_sql = text("""
            SELECT e.id, e.title, e.event_date, e.summary, e.permalink,
                   snippet(entry_fts, 1, '<mark>', '</mark>', '…', 24) AS snippet
            FROM entry_fts
            JOIN entry e ON entry_fts.rowid = e.id
            WHERE entry_fts MATCH :query
            ORDER BY rank
            LIMIT :limit OFFSET :offset
        """)
        rows = db.execute(fts_sql, {"query": safe_q, "limit": limit, "offset": offset}).fetchall()
    except Exception:
        # Fallback to LIKE if FTS fails
        rows = []
        like_q = f"%{q}%"
        entries = (
            db.query(Entry)
            .filter(
                (Entry.title.ilike(like_q))
                | (Entry.text_content.ilike(like_q))
                | (Entry.summary.ilike(like_q))
            )
            .limit(limit)
            .offset(offset)
            .all()
        )
        rows = [(e.id, e.title, e.event_date, e.summary, e.permalink, "") for e in entries]

    results = []
    for row in rows:
        entry_id, title, event_date, summary, permalink, snippet = row
        entry = db.get(Entry, entry_id)
        hero = None
        if entry and entry.hero_media:
            m = entry.hero_media
            hero = {
                "sha256": m.sha256,
                "ext": m.ext,
                "url": f"/api/media/{m.sha256}.{m.ext}",
            }
        results.append({
            "id": entry_id,
            "title": title,
            "event_date": event_date,
            "summary": summary,
            "permalink": permalink,
            "snippet": snippet,
            "hero": hero,
        })

    # Count total (approximate)
    try:
        count_sql = text("""
            SELECT COUNT(*) FROM entry_fts
            JOIN entry e ON entry_fts.rowid = e.id
            WHERE entry_fts MATCH :query
        """)
        total = db.execute(count_sql, {"query": safe_q}).scalar() or 0
    except Exception:
        total = len(results)

    return {
        "query": q,
        "total": total,
        "items": results,
        "offset": offset,
        "limit": limit,
    }
