"""Book endpoints: one payload with everything the book UI needs for its
tables of contents and page-to-page navigation.

Topics are curated tags (category='collection', slug 'topic-*') created by
scripts/assign_topics.py. Display metadata (emoji, tagline, order) lives here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from core.db.session import get_session
from core.db.models import Entry, EntryMedia, Media, EntryTag, Tag

router = APIRouter(prefix="/book", tags=["book"])

# slug -> (emoji, tagline, order); labels/colors come from the tag table
TOPIC_META = {
    "topic-lowlands": ("🌷", "Daily life, Dutch quirks, and discoveries around Amsterdam & Haarlem", 1),
    "topic-seasons": ("🍂", "Tulips, fall colors, and first frosts — the turning year in the Netherlands", 2),
    "topic-piper": ("🐾", "Poodles, highland cows, wild horses, and the neighborhood deer", 3),
    "topic-transport": ("🚲", "The curious ways the world gets around", 4),
    "topic-europe": ("🏰", "City breaks and road trips across the continent", 5),
    "topic-japan": ("🗾", "Two trips east: Tokyo, Kyoto, Osaka, Nara & Mt. Fuji", 6),
    "topic-downunder": ("🦘", "Singapore, New Zealand & Australia in one great loop", 7),
    "topic-america": ("🗽", "Stateside visits: New York, Vegas, LA & the Pacific Northwest", 8),
    "topic-sunshine": ("🏝️", "Jersey, Tenerife, Malta & Turkey — warm light and open water", 9),
    "topic-celebrations": ("🎉", "Anniversaries, holidays, and moments worth marking", 10),
}

# Entries synced after the last curation run land here so the book never breaks.
FALLBACK_TOPIC = {
    "slug": "topic-new",
    "label": "New Adventures",
    "emoji": "✨",
    "tagline": "Recently synced stories awaiting a chapter",
    "color": "#8b6f4e",
    "order": 99,
}


def build_toc(db: Session) -> dict:
    """Full table of contents: chapters + every entry in book (date) order.

    Shared by the /api/book/toc endpoint and the static-book exporter.
    """
    topic_tags = (
        db.query(Tag).filter(Tag.slug.like("topic-%")).all()
    )
    topics = []
    for t in topic_tags:
        emoji, tagline, order = TOPIC_META.get(t.slug, ("📖", "", 50))
        topics.append({
            "slug": t.slug,
            "label": t.label,
            "emoji": emoji,
            "tagline": tagline,
            "color": t.color,
            "order": order,
        })
    topics.sort(key=lambda x: x["order"])

    # Map entry -> topic slug
    topic_by_entry = {
        et.entry_id: et.tag.slug
        for et in db.query(EntryTag).join(Tag).filter(Tag.slug.like("topic-%")).all()
    }

    entries = (
        db.query(Entry)
        .options(
            joinedload(Entry.hero_media),
            joinedload(Entry.media_items).joinedload(EntryMedia.media),
            joinedload(Entry.entry_tags).joinedload(EntryTag.tag),
        )
        .all()
    )

    # Book order: chronological. Entries were imported newest-first, so on a
    # same-day tie the higher id is the earlier post — order by id DESC.
    entries.sort(key=lambda e: (e.event_date or "9999", -e.id))

    items = []
    needs_fallback = False
    for e in entries:
        cover = None
        hero = e.hero_media
        if hero is not None and hero.status == "downloaded":
            cover = hero
        else:
            for em in sorted(e.media_items, key=lambda x: x.position):
                if em.media and em.media.status == "downloaded":
                    cover = em.media
                    break

        photo_count = sum(
            1 for em in e.media_items if em.media and em.media.status == "downloaded"
        )

        snippet = (e.summary or e.text_content or "").strip().replace("\n", " ")
        if len(snippet) > 180:
            snippet = snippet[:180].rsplit(" ", 1)[0] + "…"

        topic = topic_by_entry.get(e.id)
        if topic is None:
            topic = FALLBACK_TOPIC["slug"]
            needs_fallback = True

        keywords = [
            et.tag.label for et in e.entry_tags
            if et.tag and et.tag.category == "keyword"
        ]

        items.append({
            "id": e.id,
            "title": e.title,
            "event_date": e.event_date,
            "topic": topic,
            "photos": photo_count,
            "snippet": snippet,
            "keywords": keywords,
            "cover": {
                "url": f"/api/media/{cover.sha256}.{cover.ext}",
                "width": cover.width,
                "height": cover.height,
            } if cover else None,
        })

    if needs_fallback:
        topics.append(dict(FALLBACK_TOPIC))

    return {"topics": topics, "entries": items}


@router.get("/toc")
def book_toc(db: Session = Depends(get_session)):
    return build_toc(db)
