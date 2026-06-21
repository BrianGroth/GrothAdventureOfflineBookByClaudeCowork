"""Statistics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from core.db.session import get_session
from core.db.models import Entry, Media, Tag, Source, IngestRun

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(db: Session = Depends(get_session)):
    """Return overall database statistics."""
    entry_count = db.query(func.count(Entry.id)).scalar() or 0
    media_count = db.query(func.count(Media.id)).filter(Media.status == "downloaded").scalar() or 0
    tag_count = db.query(func.count(Tag.id)).scalar() or 0

    # Date range
    date_row = db.query(
        func.min(Entry.event_date).label("earliest"),
        func.max(Entry.event_date).label("latest"),
    ).first()

    # Year breakdown
    year_rows = (
        db.query(
            func.substr(Entry.event_date, 1, 4).label("year"),
            func.count(Entry.id).label("count"),
        )
        .filter(Entry.event_date.isnot(None))
        .group_by(func.substr(Entry.event_date, 1, 4))
        .order_by(func.substr(Entry.event_date, 1, 4))
        .all()
    )

    # Last sync
    last_run = (
        db.query(IngestRun)
        .filter(IngestRun.status == "completed")
        .order_by(IngestRun.completed_at.desc())
        .first()
    )

    # Media size total
    size_row = db.query(func.sum(Media.file_size)).filter(Media.status == "downloaded").scalar()

    return {
        "entry_count": entry_count,
        "media_count": media_count,
        "tag_count": tag_count,
        "earliest_date": date_row.earliest if date_row else None,
        "latest_date": date_row.latest if date_row else None,
        "total_media_bytes": size_row or 0,
        "last_sync": last_run.completed_at if last_run else None,
        "years": [{"year": r.year, "count": r.count} for r in year_rows],
    }


@router.get("/sources")
def source_stats(db: Session = Depends(get_session)):
    """Per-source statistics."""
    sources = db.query(Source).all()
    result = []
    for src in sources:
        ec = db.query(func.count(Entry.id)).filter(Entry.source_id == src.id).scalar() or 0
        mc = db.query(func.count(Media.id)).filter(
            Media.source_id == src.id, Media.status == "downloaded"
        ).scalar() or 0
        last = (
            db.query(IngestRun)
            .filter(IngestRun.source_id == src.id)
            .order_by(IngestRun.started_at.desc())
            .first()
        )
        result.append({
            "id": src.id,
            "name": src.name,
            "type": src.type,
            "base_url": src.base_url,
            "entries": ec,
            "media": mc,
            "last_sync": last.completed_at if last else None,
            "last_sync_status": last.status if last else None,
        })
    return result
