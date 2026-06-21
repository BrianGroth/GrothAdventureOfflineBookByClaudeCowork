"""SQLAlchemy ORM models for the Groth Adventures Scrapbook database."""
from __future__ import annotations

from sqlalchemy import (
    Column,
    Integer,
    Text,
    Float as Real,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, relationship


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.close()


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "source"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    base_url = Column(Text)
    config_json = Column(Text, nullable=False, default="{}")
    created_at = Column(Text, nullable=False)

    ingest_runs = relationship("IngestRun", back_populates="source", cascade="all, delete-orphan")
    entries = relationship("Entry", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("type", "name"),)


class IngestRun(Base):
    __tablename__ = "ingest_run"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("source.id", ondelete="CASCADE"), nullable=False)
    mode = Column(Text, nullable=False)
    started_at = Column(Text, nullable=False)
    completed_at = Column(Text)
    status = Column(Text, nullable=False, default="running")
    stats_json = Column(Text, nullable=False, default="{}")
    error_message = Column(Text)

    source = relationship("Source", back_populates="ingest_runs")

    __table_args__ = (
        CheckConstraint("mode IN ('full','incremental','single')", name="ck_ingest_run_mode"),
        CheckConstraint("status IN ('running','completed','failed','aborted')", name="ck_ingest_run_status"),
    )


class Entry(Base):
    __tablename__ = "entry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("source.id", ondelete="CASCADE"), nullable=False)
    source_entry_id = Column(Text, nullable=False)
    permalink = Column(Text, nullable=False)
    title = Column(Text, nullable=False, default="")
    event_date = Column(Text)
    publish_date = Column(Text)
    author = Column(Text)
    html_content = Column(Text, nullable=False, default="")
    text_content = Column(Text, nullable=False, default="")
    summary = Column(Text, nullable=False, default="")
    hero_media_id = Column(Integer, ForeignKey("media.id", ondelete="SET NULL"))
    review_flag = Column(Integer, nullable=False, default=0)
    review_note = Column(Text)
    ingest_run_id = Column(Integer, ForeignKey("ingest_run.id", ondelete="SET NULL"))
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    source = relationship("Source", back_populates="entries")
    hero_media = relationship("Media", foreign_keys=[hero_media_id])
    media_items = relationship("EntryMedia", back_populates="entry", cascade="all, delete-orphan")
    entry_tags = relationship("EntryTag", back_populates="entry", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("source_id", "source_entry_id"),)


class Media(Base):
    __tablename__ = "media"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("source.id", ondelete="CASCADE"), nullable=False)
    original_url = Column(Text, nullable=False)
    sha256 = Column(Text, nullable=False)
    ext = Column(Text, nullable=False, default="")
    mime_type = Column(Text)
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)
    exif_json = Column(Text)
    alt_text = Column(Text)
    caption = Column(Text)
    status = Column(Text, nullable=False, default="pending")
    error_message = Column(Text)
    created_at = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("source_id", "sha256"),
        CheckConstraint("status IN ('pending','downloaded','failed','skipped')", name="ck_media_status"),
    )


class EntryMedia(Base):
    __tablename__ = "entry_media"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(Integer, ForeignKey("entry.id", ondelete="CASCADE"), nullable=False)
    media_id = Column(Integer, ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    role = Column(Text, nullable=False, default="inline")

    entry = relationship("Entry", back_populates="media_items")
    media = relationship("Media")

    __table_args__ = (
        UniqueConstraint("entry_id", "media_id"),
        CheckConstraint("role IN ('hero','inline','gallery')", name="ck_entry_media_role"),
    )


class Tag(Base):
    __tablename__ = "tag"
    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(Text, nullable=False, unique=True)
    label = Column(Text, nullable=False)
    category = Column(Text, nullable=False, default="keyword")
    color = Column(Text)

    entry_tags = relationship("EntryTag", back_populates="tag", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("category IN ('year','season','keyword','location','person','collection')", name="ck_tag_category"),
    )


class EntryTag(Base):
    __tablename__ = "entry_tag"
    entry_id = Column(Integer, ForeignKey("entry.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    tag_id = Column(Integer, ForeignKey("tag.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    auto = Column(Integer, nullable=False, default=1)

    entry = relationship("Entry", back_populates="entry_tags")
    tag = relationship("Tag", back_populates="entry_tags")


class RawSnapshot(Base):
    __tablename__ = "raw_snapshot"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(Integer, ForeignKey("entry.id", ondelete="CASCADE"), nullable=False)
    ingest_run_id = Column(Integer, ForeignKey("ingest_run.id", ondelete="SET NULL"))
    fetched_at = Column(Text, nullable=False)
    http_status = Column(Integer)
    content_length = Column(Integer)
    file_path = Column(Text, nullable=False)
    headers_path = Column(Text, nullable=False)

    entry = relationship("Entry")


class SchemaVersion(Base):
    __tablename__ = "schema_version"
    version = Column(Integer, primary_key=True)
    applied_at = Column(Text, nullable=False)

    CURRENT = 1
