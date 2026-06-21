"""Entry endpoints."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from core.db.session import get_session
from core.db.models import Entry, EntryMedia, Media, EntryTag, Tag

router = APIRouter(prefix="/entries", tags=["entries"])


def _media_url(request: Request, m: Media) -> str:
    return str(request.url_for("serve_media", sha256=m.sha256, ext=m.ext))


def _entry_dict(entry: Entry, request: Request, include_html: bool = False) -> dict:
    hero = None
    if entry.hero_media:
        hero = {
            "id": entry.hero_media.id,
            "sha256": entry.hero_media.sha256,
            "ext": entry.hero_media.ext,
            "width": entry.hero_media.width,
            "height": entry.hero_media.height,
            "alt_text": entry.hero_media.alt_text,
            "url": f"/api/media/{entry.hero_media.sha256}.{entry.hero_media.ext}",
        }

    tags = [
        {"slug": et.tag.slug, "label": et.tag.label, "category": et.tag.category, "color": et.tag.color}
        for et in entry.entry_tags
        if et.tag
    ]

    media_items = [
        {
            "id": em.media_id,
            "sha256": em.media.sha256,
            "ext": em.media.ext,
            "width": em.media.width,
            "height": em.media.height,
            "alt_text": em.media.alt_text,
            "caption": em.media.caption,
            "role": em.role,
            "position": em.position,
            "url": f"/api/media/{em.media.sha256}.{em.media.ext}",
        }
        for em in sorted(entry.media_items, key=lambda x: x.position)
        if em.media and em.media.status == "downloaded"
    ]

    result = {
        "id": entry.id,
        "source_entry_id": entry.source_entry_id,
        "permalink": entry.permalink,
        "title": entry.title,
        "event_date": entry.event_date,
        "publish_date": entry.publish_date,
        "author": entry.author,
        "summary": entry.summary,
        "hero": hero,
        "tags": tags,
        "media": media_items,
        "review_flag": bool(entry.review_flag),
        "review_note": entry.review_note,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }
    if include_html:
        result["html_content"] = entry.html_content

    return result


@router.get("")
def list_entries(
    request: Request,
    cursor: Optional[int] = Query(None, description="Pagination cursor (last entry id)"),
    limit: int = Query(20, ge=1, le=100),
    year: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    review_flag: Optional[bool] = Query(None),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_session),
):
    """List entries with cursor-based pagination."""
    query = db.query(Entry)

    if year:
        query = query.filter(Entry.event_date.like(f"{year}-%"))

    if tag:
        query = query.join(EntryTag).join(Tag).filter(Tag.slug == tag)

    if review_flag is not None:
        query = query.filter(Entry.review_flag == (1 if review_flag else 0))

    if order == "desc":
        query = query.order_by(Entry.event_date.desc().nullslast(), Entry.id.desc())
        if cursor is not None:
            anchor = db.get(Entry, cursor)
            if anchor:
                query = query.filter(
                    (Entry.event_date < anchor.event_date)
                    | ((Entry.event_date == anchor.event_date) & (Entry.id < anchor.id))
                )
    else:
        query = query.order_by(Entry.event_date.asc().nullsfirst(), Entry.id.asc())
        if cursor is not None:
            anchor = db.get(Entry, cursor)
            if anchor:
                query = query.filter(
                    (Entry.event_date > anchor.event_date)
                    | ((Entry.event_date == anchor.event_date) & (Entry.id > anchor.id))
                )

    entries = query.limit(limit + 1).all()
    has_more = len(entries) > limit
    entries = entries[:limit]

    return {
        "items": [_entry_dict(e, request) for e in entries],
        "next_cursor": entries[-1].id if has_more and entries else None,
        "has_more": has_more,
    }


@router.get("/by-year")
def entries_by_year(
    request: Request,
    db: Session = Depends(get_session),
):
    """Return year summary for TOC."""
    from sqlalchemy import func, extract

    rows = (
        db.query(
            func.substr(Entry.event_date, 1, 4).label("year"),
            func.count(Entry.id).label("count"),
        )
        .filter(Entry.event_date.isnot(None))
        .group_by(func.substr(Entry.event_date, 1, 4))
        .order_by(func.substr(Entry.event_date, 1, 4).desc())
        .all()
    )
    return [{"year": r.year, "count": r.count} for r in rows]


@router.get("/{entry_id}")
def get_entry(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_session),
):
    """Get a single entry with full HTML content and prev/next navigation."""
    entry = db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    result = _entry_dict(entry, request, include_html=True)

    # Adjacent entries ordered by event_date desc, id desc (same as list order)
    prev_entry = (
        db.query(Entry)
        .filter(
            (Entry.event_date > entry.event_date)
            | ((Entry.event_date == entry.event_date) & (Entry.id > entry.id))
        )
        .order_by(Entry.event_date.asc(), Entry.id.asc())
        .first()
    )
    next_entry = (
        db.query(Entry)
        .filter(
            (Entry.event_date < entry.event_date)
            | ((Entry.event_date == entry.event_date) & (Entry.id < entry.id))
        )
        .order_by(Entry.event_date.desc(), Entry.id.desc())
        .first()
    )

    result["prev"] = {"id": prev_entry.id, "title": prev_entry.title, "event_date": prev_entry.event_date} if prev_entry else None
    result["next"] = {"id": next_entry.id, "title": next_entry.title, "event_date": next_entry.event_date} if next_entry else None

    return result


@router.patch("/{entry_id}/flag")
def update_flag(
    entry_id: int,
    body: dict,
    db: Session = Depends(get_session),
):
    """Update review flag on an entry."""
    entry = db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if "review_flag" in body:
        entry.review_flag = 1 if body["review_flag"] else 0
    if "review_note" in body:
        entry.review_note = body["review_note"]
    db.commit()
    return {"ok": True}
