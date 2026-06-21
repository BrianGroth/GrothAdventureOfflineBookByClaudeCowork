"""Configuration management for the Groth Adventures Scrapbook."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"


class AppConfig:
    """Loaded application configuration."""

    def __init__(self, data_dir: Path, raw_config: dict[str, Any]):
        self.data_dir = data_dir
        self.raw = raw_config
        self.sources: list[dict[str, Any]] = raw_config.get("sources", [])

    @property
    def db_dir(self) -> Path:
        return self.data_dir / "db"

    @property
    def db_path(self) -> Path:
        return self.db_dir / "scrapbook.sqlite"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def export_dir(self) -> Path:
        return self.data_dir / "exports"

    def media_path(self, sha256: str, ext: str) -> Path:
        """Return the filesystem path for a media file given its SHA-256 hash."""
        return self.media_dir / sha256[0:2] / sha256[2:4] / f"{sha256}.{ext}"

    def raw_path(self, source_id: int, year: str, month: str, day_slug: str) -> Path:
        return self.raw_dir / str(source_id) / year / month / day_slug

    def source_by_name(self, name: str) -> dict[str, Any] | None:
        for s in self.sources:
            if s.get("name") == name:
                return s
        return None

    def ensure_dirs(self) -> None:
        """Create all required data subdirectories."""
        for d in [self.db_dir, self.media_dir, self.raw_dir, self.export_dir]:
            d.mkdir(parents=True, exist_ok=True)


def load_config(
    data_dir: Path | None = None,
    config_path: Path | None = None,
) -> AppConfig:
    """Load config from YAML file and environment overrides."""
    if data_dir is None:
        env_val = os.environ.get("SCRAPBOOK_DATA_DIR")
        data_dir = Path(env_val) if env_val else DEFAULT_DATA_DIR

    if config_path is None:
        env_val = os.environ.get("SCRAPBOOK_CONFIG")
        config_path = Path(env_val) if env_val else DEFAULT_CONFIG_PATH

    raw: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    return AppConfig(data_dir=Path(data_dir), raw_config=raw)


_global_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Return the global config, initializing if needed."""
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config


def set_config(cfg: AppConfig) -> None:
    global _global_config
    _global_config = cfg
