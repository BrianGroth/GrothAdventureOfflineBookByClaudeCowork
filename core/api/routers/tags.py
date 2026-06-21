"""Tags and collections endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.db.session import get_session
from core.db.models import Tag, EntryTag, Entry

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("")
def list_tags(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_session),
):
    """List all tags with entry counts."""
    query = (
        db.query(Tag, func.count(EntryTag.entry_id).label("count"))
        .outerjoin(EntryTag, EntryTag.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(Tag.category, Tag.label)
    )
    if category:
        query = query.filter(Tag.category == category)

    rows = query.all()
    return [
        {
            "id": t.id,
            "slug": t.slug,
            "label": t.label,
            "category": t.category,
            "color": t.color,
            "count": count,
        }
        for t, count in rows
    ]


@router.get("/collections")
def list_collections(db: Session = Depends(get_session)):
    """List collection tags."""
    tags = db.query(Tag).filter(Tag.category == "collection").order_by(Tag.label).all()
    return [
        {"id": t.id, "slug": t.slug, "label": t.label, "color": t.color}
        for t in tags
    ]


@router.get("/{slug}/entries")
def tag_entries(
    slug: str,
    cursor: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
):
    """Get entries for a specific tag."""
    tag = db.query(Tag).filter_by(slug=slug).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    query = (
        db.query(Entry)
        .join(EntryTag)
        .filter(EntryTag.tag_id == tag.id)
        .order_by(Entry.event_date.desc().nullslast(), Entry.id.desc())
    )

    if cursor:
        anchor = db.get(Entry, cursor)
        if anchor:
            query = query.filter(
                (Entry.event_date < anchor.event_date)
                | ((Entry.event_date == anchor.event_date) & (Entry.id < anchor.id))
            )

    entries = query.limit(limit + 1).all()
    has_more = len(entries) > limit
    entries = entries[:limit]

    return {
        "tag": {"slug": tag.slug, "label": tag.label, "category": tag.category},
        "items": [
            {
                "id": e.id,
                "title": e.title,
                "event_date": e.event_date,
                "summary": e.summary,
                "permalink": e.permalink,
            }
            for e in entries
        ],
        "next_cursor": entries[-1].id if has_more and entries else None,
        "has_more": has_more,
    }


@router.post("")
def create_tag(body: dict, db: Session = Depends(get_session)):
    """Create a new tag (for collections)."""
    slug = body.get("slug", "").strip()
    label = body.get("label", "").strip()
    category = body.get("category", "collection")

    if not slug or not label:
        raise HTTPException(status_code=422, detail="slug and label are required")

    existing = db.query(Tag).filter_by(slug=slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tag slug already exists")

    tag = Tag(slug=slug, label=label, category=category, color=body.get("color"))
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return {"id": tag.id, "slug": tag.slug, "label": tag.label, "category": tag.category}


@router.post("/entry/{entry_id}")
def add_entry_tag(entry_id: int, body: dict, db: Session = Depends(get_session)):
    """Add a tag to an entry."""
    entry = db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    tag_slug = body.get("slug")
    if not tag_slug:
        raise HTTPException(status_code=422, detail="slug required")

    tag = db.query(Tag).filter_by(slug=tag_slug).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    existing = db.query(EntryTag).filter_by(entry_id=entry_id, tag_id=tag.id).first()
    if not existing:
        et = EntryTag(entry_id=entry_id, tag_id=tag.id, auto=0)
        db.add(et)
        db.commit()

    return {"ok": True}


@router.delete("/entry/{entry_id}/{tag_slug}")
def remove_entry_tag(entry_id: int, tag_slug: str, db: Session = Depends(get_session)):
    """Remove a tag from an entry."""
    tag = db.query(Tag).filter_by(slug=tag_slug).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    et = db.query(EntryTag).filter_by(entry_id=entry_id, tag_id=tag.id).first()
    if et:
        db.delete(et)
        db.commit()

    return {"ok": True}
