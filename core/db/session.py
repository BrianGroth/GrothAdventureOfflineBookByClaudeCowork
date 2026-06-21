"""Database session factory and utilities."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from core.db.models import Base, SchemaVersion

_engine = None
_SessionLocal = None


def init_engine(db_url: str):
    """Initialize the SQLAlchemy engine with the given URL. Idempotent."""
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine  # Already initialized
    _engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_engine():
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Run 'scrapbook init' first.")
    return _engine


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session."""
    if _SessionLocal is None:
        raise RuntimeError("Database engine not initialized.")
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_local() -> Session:
    """Return a new session (caller must close)."""
    if _SessionLocal is None:
        raise RuntimeError("Database engine not initialized.")
    return _SessionLocal()


def check_schema_version(db: Session) -> bool:
    """Return True if schema is at expected version."""
    try:
        row = db.execute(
            text("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        ).fetchone()
        return row is not None and row[0] == SchemaVersion.CURRENT
    except Exception:
        return False


def run_migrations(db_url: str) -> None:
    """Run Alembic migrations programmatically."""
    from alembic.config import Config
    from alembic import command
    import os

    # Find alembic.ini relative to this file
    ini_path = Path(__file__).parent.parent.parent / "alembic.ini"

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    alembic_cfg.set_main_option(
        "script_location",
        str(Path(__file__).parent / "migrations"),
    )
    command.upgrade(alembic_cfg, "head")
