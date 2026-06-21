"""Initial schema - all tables, FTS5 virtual tables, and triggers.

Revision ID: 0001
Revises:
Create Date: 2026-06-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Core tables
    op.create_table(
        "source",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("base_url", sa.Text),
        sa.Column("config_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.UniqueConstraint("type", "name"),
    )

    op.create_table(
        "ingest_run",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("source.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.Text, nullable=False),
        sa.Column("started_at", sa.Text, nullable=False),
        sa.Column("completed_at", sa.Text),
        sa.Column("status", sa.Text, nullable=False, server_default="running"),
        sa.Column("stats_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text),
        sa.CheckConstraint("mode IN ('full','incremental','single')", name="ck_ingest_run_mode"),
        sa.CheckConstraint("status IN ('running','completed','failed','aborted')", name="ck_ingest_run_status"),
    )

    op.create_table(
        "media",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("source.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_url", sa.Text, nullable=False),
        sa.Column("sha256", sa.Text, nullable=False),
        sa.Column("ext", sa.Text, nullable=False, server_default=""),
        sa.Column("mime_type", sa.Text),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("file_size", sa.Integer),
        sa.Column("exif_json", sa.Text),
        sa.Column("alt_text", sa.Text),
        sa.Column("caption", sa.Text),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.UniqueConstraint("source_id", "sha256"),
        sa.CheckConstraint("status IN ('pending','downloaded','failed','skipped')", name="ck_media_status"),
    )

    op.create_table(
        "entry",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("source.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_entry_id", sa.Text, nullable=False),
        sa.Column("permalink", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False, server_default=""),
        sa.Column("event_date", sa.Text),
        sa.Column("publish_date", sa.Text),
        sa.Column("author", sa.Text),
        sa.Column("html_content", sa.Text, nullable=False, server_default=""),
        sa.Column("text_content", sa.Text, nullable=False, server_default=""),
        sa.Column("summary", sa.Text, nullable=False, server_default=""),
        sa.Column("hero_media_id", sa.Integer, sa.ForeignKey("media.id", ondelete="SET NULL")),
        sa.Column("review_flag", sa.Integer, nullable=False, server_default="0"),
        sa.Column("review_note", sa.Text),
        sa.Column("ingest_run_id", sa.Integer, sa.ForeignKey("ingest_run.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
        sa.UniqueConstraint("source_id", "source_entry_id"),
    )

    op.create_table(
        "entry_media",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("entry_id", sa.Integer, sa.ForeignKey("entry.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_id", sa.Integer, sa.ForeignKey("media.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("role", sa.Text, nullable=False, server_default="inline"),
        sa.UniqueConstraint("entry_id", "media_id"),
        sa.CheckConstraint("role IN ('hero','inline','gallery')", name="ck_entry_media_role"),
    )

    op.create_table(
        "tag",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("slug", sa.Text, nullable=False, unique=True),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("category", sa.Text, nullable=False, server_default="keyword"),
        sa.Column("color", sa.Text),
        sa.CheckConstraint(
            "category IN ('year','season','keyword','location','person','collection')",
            name="ck_tag_category",
        ),
    )

    op.create_table(
        "entry_tag",
        sa.Column("entry_id", sa.Integer, sa.ForeignKey("entry.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tag.id", ondelete="CASCADE"), nullable=False),
        sa.Column("auto", sa.Integer, nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("entry_id", "tag_id"),
    )

    op.create_table(
        "raw_snapshot",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("entry_id", sa.Integer, sa.ForeignKey("entry.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ingest_run_id", sa.Integer, sa.ForeignKey("ingest_run.id", ondelete="SET NULL")),
        sa.Column("fetched_at", sa.Text, nullable=False),
        sa.Column("http_status", sa.Integer),
        sa.Column("content_length", sa.Integer),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("headers_path", sa.Text, nullable=False),
    )

    op.create_table(
        "schema_version",
        sa.Column("version", sa.Integer, primary_key=True),
        sa.Column("applied_at", sa.Text, nullable=False),
    )

    # Indexes
    op.create_index("idx_entry_event_date", "entry", ["event_date"])
    op.create_index("idx_entry_source", "entry", ["source_id"])
    op.create_index("idx_entry_hero_media", "entry", ["hero_media_id"])
    op.create_index("idx_media_sha256", "media", ["sha256"])
    op.create_index("idx_entry_tag_tag", "entry_tag", ["tag_id"])
    op.create_index("idx_ingest_run_source", "ingest_run", ["source_id"])

    # FTS5 virtual table for full-text search
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS entry_fts USING fts5(
            title,
            text_content,
            summary,
            content='entry',
            content_rowid='id',
            tokenize='unicode61 remove_diacritics 1'
        )
    """)

    # Triggers to keep FTS in sync
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS entry_ai AFTER INSERT ON entry BEGIN
            INSERT INTO entry_fts(rowid, title, text_content, summary)
            VALUES (new.id, new.title, new.text_content, new.summary);
        END
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS entry_au AFTER UPDATE ON entry BEGIN
            INSERT INTO entry_fts(entry_fts, rowid, title, text_content, summary)
            VALUES ('delete', old.id, old.title, old.text_content, old.summary);
            INSERT INTO entry_fts(rowid, title, text_content, summary)
            VALUES (new.id, new.title, new.text_content, new.summary);
        END
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS entry_ad AFTER DELETE ON entry BEGIN
            INSERT INTO entry_fts(entry_fts, rowid, title, text_content, summary)
            VALUES ('delete', old.id, old.title, old.text_content, old.summary);
        END
    """)

    # Insert initial schema version
    op.execute("INSERT INTO schema_version (version, applied_at) VALUES (1, datetime('now'))")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS entry_ad")
    op.execute("DROP TRIGGER IF EXISTS entry_au")
    op.execute("DROP TRIGGER IF EXISTS entry_ai")
    op.execute("DROP TABLE IF EXISTS entry_fts")
    op.drop_table("schema_version")
    op.drop_table("raw_snapshot")
    op.drop_table("entry_tag")
    op.drop_table("tag")
    op.drop_table("entry_media")
    op.drop_table("entry")
    op.drop_table("media")
    op.drop_table("ingest_run")
    op.drop_table("source")
