"""Media serving endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from core.db.session import get_session
from core.db.models import Media

router = APIRouter(prefix="/media", tags=["media"])


def _get_cfg(request: Request):
    return request.app.state.cfg


@router.get("/{sha256}.{ext}", name="serve_media")
def serve_media(
    sha256: str,
    ext: str,
    request: Request,
    db: Session = Depends(get_session),
):
    """Serve a media file by SHA-256 hash and extension."""
    cfg = _get_cfg(request)

    # Validate the media exists in DB
    media = db.query(Media).filter_by(sha256=sha256).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    path = cfg.media_path(sha256, ext)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media file not on disk")

    mime = media.mime_type or "application/octet-stream"
    return FileResponse(
        path=str(path),
        media_type=mime,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": sha256[:16],
        },
    )


@router.get("/{media_id}/info")
def media_info(
    media_id: int,
    db: Session = Depends(get_session),
):
    """Get metadata for a media item."""
    media = db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return {
        "id": media.id,
        "sha256": media.sha256,
        "ext": media.ext,
        "mime_type": media.mime_type,
        "width": media.width,
        "height": media.height,
        "file_size": media.file_size,
        "alt_text": media.alt_text,
        "caption": media.caption,
        "original_url": media.original_url,
        "status": media.status,
    }
