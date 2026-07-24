"""Groth Adventures Scrapbook CLI."""
from __future__ import annotations

import io
import json
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Force UTF-8 output on Windows so Rich can render checkmarks etc.
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(
    name="scrapbook",
    help="Groth Adventures Offline Scrapbook - sync and browse your family adventure blog.",
    no_args_is_help=True,
)
console = Console()


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_and_init(data_dir: Optional[Path], config_path: Optional[Path]):
    """Load config, init engine, verify schema."""
    from core.config import load_config, set_config
    from core.db.session import init_engine

    cfg = load_config(data_dir=data_dir, config_path=config_path)
    set_config(cfg)

    if not cfg.db_path.exists():
        rprint(f"[red]Database not found at {cfg.db_path}[/red]")
        rprint("Run [bold]scrapbook init[/bold] first.")
        raise typer.Exit(code=1)

    init_engine(cfg.db_url)
    return cfg


def _check_schema_or_exit(cfg):
    """Verify schema version or exit with code 3."""
    from core.db.session import get_session_local, check_schema_version

    db = get_session_local()
    try:
        if not check_schema_version(db):
            rprint("[red]Schema version mismatch.[/red] Run [bold]scrapbook init[/bold] to migrate.")
            raise typer.Exit(code=3)
    finally:
        db.close()


@app.command()
def init(
    data_dir: Optional[Path] = typer.Option(None, "--data-dir", help="Path to data directory"),
    config: Optional[Path] = typer.Option(None, "--config", help="Path to sources.yaml"),
):
    """Initialize the scrapbook database and data directories."""
    from core.config import load_config, set_config
    from core.db.session import init_engine, run_migrations

    cfg = load_config(data_dir=data_dir, config_path=config)
    set_config(cfg)

    rprint(f"[bold]Data directory:[/bold] {cfg.data_dir}")
    cfg.ensure_dirs()
    rprint("[green]✓[/green] Directories created")

    engine = init_engine(cfg.db_url)
    rprint(f"[bold]Database:[/bold] {cfg.db_path}")

    try:
        run_migrations(cfg.db_url)
        rprint("[green]✓[/green] Schema migrations applied")
    except Exception as e:
        rprint(f"[red]Migration failed:[/red] {e}")
        raise typer.Exit(code=1)

    # Register sources from config
    if cfg.sources:
        from core.db.session import get_session_local
        from core.db.models import Source

        db = get_session_local()
        try:
            for src_cfg in cfg.sources:
                existing = db.query(Source).filter_by(
                    type=src_cfg.get("type", "wordpress"),
                    name=src_cfg["name"],
                ).first()
                if not existing:
                    src = Source(
                        type=src_cfg.get("type", "wordpress"),
                        name=src_cfg["name"],
                        base_url=src_cfg.get("base_url", ""),
                        config_json=json.dumps(src_cfg),
                        created_at=_now_utc(),
                    )
                    db.add(src)
            db.commit()
            rprint(f"[green]✓[/green] {len(cfg.sources)} source(s) registered")
        finally:
            db.close()

    rprint("[bold green]Initialization complete.[/bold green]")


@app.command()
def status(
    source: Optional[str] = typer.Option(None, "--source", help="Filter by source name"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    data_dir: Optional[Path] = typer.Option(None, "--data-dir"),
    config: Optional[Path] = typer.Option(None, "--config"),
):
    """Show sync status and database statistics."""
    cfg = _load_and_init(data_dir, config)
    _check_schema_or_exit(cfg)

    from core.db.session import get_session_local
    from core.db.models import Source, IngestRun, Entry, Media
    from sqlalchemy import func

    db = get_session_local()
    try:
        query = db.query(Source)
        if source:
            query = query.filter(Source.name == source)
        sources = query.all()

        if not sources:
            rprint("[yellow]No sources found.[/yellow]")
            return

        result = []
        for src in sources:
            entry_count = db.query(func.count(Entry.id)).filter(Entry.source_id == src.id).scalar()
            media_count = db.query(func.count(Media.id)).filter(Media.source_id == src.id).scalar()
            last_run = (
                db.query(IngestRun)
                .filter(IngestRun.source_id == src.id)
                .order_by(IngestRun.started_at.desc())
                .first()
            )

            info = {
                "source": src.name,
                "type": src.type,
                "base_url": src.base_url,
                "entries": entry_count,
                "media": media_count,
                "last_sync": last_run.completed_at if last_run else None,
                "last_sync_status": last_run.status if last_run else None,
                "last_sync_stats": json.loads(last_run.stats_json) if last_run else {},
            }
            result.append(info)

        if as_json:
            print(json.dumps(result, indent=2))
            return

        for info in result:
            table = Table(title=f"Source: {info['source']}", show_header=False)
            table.add_column("Key", style="bold")
            table.add_column("Value")
            table.add_row("Type", info["type"])
            table.add_row("Base URL", info["base_url"] or "—")
            table.add_row("Entries", str(info["entries"]))
            table.add_row("Media files", str(info["media"]))
            table.add_row("Last sync", info["last_sync"] or "Never")
            table.add_row("Last sync status", info["last_sync_status"] or "—")
            if info["last_sync_stats"]:
                for k, v in info["last_sync_stats"].items():
                    table.add_row(f"  {k}", str(v))
            console.print(table)

    finally:
        db.close()


@app.command()
def sync(
    source: str = typer.Option(..., "--source", help="Source name to sync"),
    full: bool = typer.Option(False, "--full", help="Full re-sync (ignore last cursor)"),
    deep: bool = typer.Option(
        False,
        "--deep",
        help="Also walk /YYYY/MM/ date archives. Needed to reach posts older than "
             "the sitemap's ~1000-URL cap. Slower discovery; run once for a backfill.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Fetch and parse but don't write to DB"),
    max_posts: Optional[int] = typer.Option(None, "--max-posts", help="Limit number of posts"),
    since: Optional[str] = typer.Option(None, "--since", help="Only sync posts since date (YYYY-MM-DD)"),
    no_media: bool = typer.Option(False, "--no-media", help="Skip media download"),
    concurrency: int = typer.Option(3, "--concurrency", help="Concurrent media downloads"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    data_dir: Optional[Path] = typer.Option(None, "--data-dir"),
    config: Optional[Path] = typer.Option(None, "--config"),
):
    """Sync posts from a configured source."""
    cfg = _load_and_init(data_dir, config)
    _check_schema_or_exit(cfg)

    src_cfg = cfg.source_by_name(source)
    if not src_cfg:
        rprint(f"[red]Source '{source}' not found in config.[/red]")
        raise typer.Exit(code=1)

    from core.db.session import get_session_local
    from core.db.models import Source as SourceModel, IngestRun
    from core.connectors.wordpress import WordPressConnector

    db = get_session_local()
    try:
        src_model = db.query(SourceModel).filter_by(name=source).first()
        if not src_model:
            rprint(f"[red]Source '{source}' not in database. Run 'scrapbook init'.[/red]")
            raise typer.Exit(code=1)

        mode = "full" if full else "incremental"
        run = IngestRun(
            source_id=src_model.id,
            mode=mode,
            started_at=_now_utc(),
            status="running",
        )
        if not dry_run:
            db.add(run)
            db.commit()
            db.refresh(run)

        rprint(f"[bold]Syncing source:[/bold] {source} (mode={mode})")
        if dry_run:
            rprint("[yellow]DRY RUN — no changes will be written[/yellow]")

        connector = WordPressConnector(
            cfg=cfg,
            source_model=src_model,
            source_config=src_cfg,
            ingest_run_id=run.id if not dry_run else None,
            dry_run=dry_run,
            verbose=verbose,
            max_posts=max_posts,
            since=since,
            no_media=no_media,
            concurrency=concurrency,
            deep=deep,
        )

        import asyncio
        stats = asyncio.run(connector.run_sync(db, full=full))

        if not dry_run:
            run.completed_at = _now_utc()
            run.status = "completed"
            run.stats_json = json.dumps(stats)
            db.commit()

        rprint(Panel(
            f"[green]Sync complete[/green]\n"
            + "\n".join(f"  {k}: {v}" for k, v in stats.items()),
            title="Results",
        ))

    except Exception as e:
        rprint(f"[red]Sync failed:[/red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        if not dry_run:
            try:
                run.completed_at = _now_utc()
                run.status = "failed"
                run.error_message = str(e)
                db.commit()
            except Exception:
                pass
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command()
def serve(
    port: int = typer.Option(8420, "--port", "-p", help="Port to listen on"),
    data_dir: Optional[Path] = typer.Option(None, "--data-dir"),
    config: Optional[Path] = typer.Option(None, "--config"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser"),
    self_check: bool = typer.Option(False, "--self-check", help="Health check and exit"),
):
    """Start the local web server."""
    cfg = _load_and_init(data_dir, config)
    _check_schema_or_exit(cfg)

    import uvicorn
    from core.api.app import create_app

    api_app = create_app(cfg)

    if self_check:
        rprint("[green]Self-check passed.[/green]")
        return

    url = f"http://127.0.0.1:{port}"
    rprint(f"[bold]Starting server at[/bold] {url}")

    if not no_browser:
        import threading
        import time
        def _open():
            time.sleep(1.5)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(
        api_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )


@app.command()
def review(
    no_browser: bool = typer.Option(False, "--no-browser"),
    list_only: bool = typer.Option(False, "--list", help="List flagged entries"),
    port: int = typer.Option(8420, "--port"),
    data_dir: Optional[Path] = typer.Option(None, "--data-dir"),
    config: Optional[Path] = typer.Option(None, "--config"),
):
    """Review flagged entries."""
    cfg = _load_and_init(data_dir, config)
    _check_schema_or_exit(cfg)

    from core.db.session import get_session_local
    from core.db.models import Entry

    db = get_session_local()
    try:
        flagged = db.query(Entry).filter(Entry.review_flag == 1).all()
        if not flagged:
            rprint("[green]No flagged entries.[/green]")
            return

        rprint(f"[yellow]{len(flagged)} flagged entries:[/yellow]")
        for e in flagged:
            rprint(f"  [{e.id}] {e.event_date or '?'} — {e.title}")
            if e.review_note:
                rprint(f"       Note: {e.review_note}")

        if not list_only:
            url = f"http://127.0.0.1:{port}/?review=1"
            if not no_browser:
                rprint(f"\nOpening review UI at {url}")
                import subprocess
                subprocess.Popen(["scrapbook", "serve", "--port", str(port), "--no-browser"])
                import time; time.sleep(2)
                webbrowser.open(url)
    finally:
        db.close()


@app.command()
def reindex(
    fts: bool = typer.Option(False, "--fts", help="Rebuild FTS5 index"),
    thumbnails: bool = typer.Option(False, "--thumbnails", help="Regenerate thumbnails"),
    tags: bool = typer.Option(False, "--tags", help="Re-run auto-tagging"),
    reparse_snapshots: bool = typer.Option(False, "--reparse-snapshots"),
    entry_id: Optional[int] = typer.Option(None, "--entry-id"),
    data_dir: Optional[Path] = typer.Option(None, "--data-dir"),
    config: Optional[Path] = typer.Option(None, "--config"),
):
    """Rebuild indexes, thumbnails, or tags."""
    cfg = _load_and_init(data_dir, config)
    _check_schema_or_exit(cfg)

    from core.db.session import get_session_local
    from sqlalchemy import text

    db = get_session_local()
    try:
        if fts:
            rprint("Rebuilding FTS5 index...")
            db.execute(text("INSERT INTO entry_fts(entry_fts) VALUES('rebuild')"))
            db.commit()
            rprint("[green]✓[/green] FTS5 index rebuilt")

        if tags:
            from core.connectors.wordpress import apply_auto_tags
            from core.db.models import Entry

            query = db.query(Entry)
            if entry_id:
                query = query.filter(Entry.id == entry_id)

            entries = query.all()
            rprint(f"Re-tagging {len(entries)} entries...")
            for entry in entries:
                apply_auto_tags(db, entry, cfg)
            db.commit()
            rprint(f"[green]✓[/green] Tags updated for {len(entries)} entries")

        if thumbnails:
            rprint("[yellow]Thumbnail regeneration not yet implemented[/yellow]")

        if not any([fts, tags, thumbnails, reparse_snapshots]):
            rprint("[yellow]Specify at least one flag: --fts, --thumbnails, --tags, --reparse-snapshots[/yellow]")
    finally:
        db.close()


@app.command()
def export(
    format: str = typer.Option("bundle", "--format"),
    output: Optional[Path] = typer.Option(None, "--output"),
    collection: Optional[str] = typer.Option(None, "--collection"),
    since: Optional[str] = typer.Option(None, "--since"),
    no_raw_snapshots: bool = typer.Option(False, "--no-raw-snapshots"),
    data_dir: Optional[Path] = typer.Option(None, "--data-dir"),
    config: Optional[Path] = typer.Option(None, "--config"),
):
    """Export scrapbook as a portable bundle."""
    cfg = _load_and_init(data_dir, config)
    _check_schema_or_exit(cfg)

    if format == "static-book":
        # A plain folder that works by double-clicking index.html — for USB
        # sticks and archives. Photos are copied incrementally (by content
        # hash), so re-exporting after a sync only adds what's new.
        from core.static_export import export_static_book
        from core.db.session import get_session_local

        dist_dir = Path(__file__).parent.parent / "app" / "dist"
        out_dir = output if output is not None else cfg.export_dir / "static-book"

        db = get_session_local()
        try:
            stats = export_static_book(db, cfg, dist_dir, Path(out_dir))
        except FileNotFoundError as exc:
            rprint(f"[red]{exc}[/red]")
            raise typer.Exit(code=1)
        finally:
            db.close()

        rprint(f"[green]✓[/green] Static book written to [bold]{out_dir}[/bold]")
        rprint(
            f"  {stats['entries']} stories · "
            f"{stats['photos_copied']} photos copied, "
            f"{stats['photos_already_there']} already there"
            + (f", [yellow]{stats['photos_missing']} missing[/yellow]" if stats["photos_missing"] else "")
        )
        rprint("  Copy the folder anywhere (USB stick, cloud drive) — open index.html to read the book.")
        return

    if format != "bundle":
        rprint(f"[red]Unknown format: {format}. Supported: 'bundle', 'static-book'.[/red]")
        raise typer.Exit(code=1)

    import zipfile
    import shutil

    if output is None:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = cfg.export_dir / f"scrapbook-bundle-{ts}.zip"

    output.parent.mkdir(parents=True, exist_ok=True)

    from core.db.session import get_session_local
    from core.db.models import Entry, EntryMedia, Media
    from sqlalchemy import text

    db = get_session_local()
    try:
        query = db.query(Entry)
        if since:
            query = query.filter(Entry.event_date >= since)
        if collection:
            from core.db.models import EntryTag, Tag
            tag = db.query(Tag).filter_by(slug=collection).first()
            if tag:
                query = query.join(EntryTag).filter(EntryTag.tag_id == tag.id)

        entries = query.all()
        rprint(f"Exporting {len(entries)} entries to {output}...")

        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write DB snapshot
            zf.write(cfg.db_path, "db/scrapbook.sqlite")

            # Write media files referenced by selected entries
            entry_ids = [e.id for e in entries]
            if entry_ids:
                media_items = (
                    db.query(Media)
                    .join(EntryMedia)
                    .filter(EntryMedia.entry_id.in_(entry_ids))
                    .all()
                )
                for m in media_items:
                    src_path = cfg.media_path(m.sha256, m.ext)
                    if src_path.exists():
                        arcname = f"media/{m.sha256[0:2]}/{m.sha256[2:4]}/{m.sha256}.{m.ext}"
                        zf.write(src_path, arcname)

            # Write manifest
            manifest = {
                "version": 1,
                "created_at": _now_utc(),
                "entry_count": len(entries),
                "collection": collection,
                "since": since,
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        size_mb = output.stat().st_size / 1024 / 1024
        rprint(f"[green]✓[/green] Bundle created: {output} ({size_mb:.1f} MB)")
    finally:
        db.close()


@app.command()
def verify_bundle(
    path: Path = typer.Argument(..., help="Path to bundle zip file"),
):
    """Verify a scrapbook bundle."""
    import zipfile

    if not path.exists():
        rprint(f"[red]File not found: {path}[/red]")
        raise typer.Exit(code=1)

    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        if "manifest.json" not in names:
            rprint("[red]Invalid bundle: missing manifest.json[/red]")
            raise typer.Exit(code=1)
        if "db/scrapbook.sqlite" not in names:
            rprint("[red]Invalid bundle: missing db/scrapbook.sqlite[/red]")
            raise typer.Exit(code=1)

        manifest = json.loads(zf.read("manifest.json"))
        rprint(Panel(
            f"Version: {manifest.get('version')}\n"
            f"Created: {manifest.get('created_at')}\n"
            f"Entries: {manifest.get('entry_count')}\n"
            f"Collection: {manifest.get('collection') or 'all'}",
            title="Bundle Manifest",
        ))
        rprint(f"[green]✓[/green] Bundle is valid ({len(names)} files)")


@app.command()
def open_bundle(
    path: Path = typer.Argument(..., help="Path to bundle zip file"),
    port: int = typer.Option(8420, "--port"),
    no_browser: bool = typer.Option(False, "--no-browser"),
):
    """Extract and serve a scrapbook bundle."""
    import zipfile
    import tempfile

    if not path.exists():
        rprint(f"[red]File not found: {path}[/red]")
        raise typer.Exit(code=1)

    tmp = tempfile.mkdtemp(prefix="scrapbook-bundle-")
    rprint(f"Extracting bundle to {tmp}...")
    with zipfile.ZipFile(path, "r") as zf:
        zf.extractall(tmp)

    from core.config import load_config, set_config
    from core.db.session import init_engine
    import uvicorn
    from core.api.app import create_app

    cfg = load_config(data_dir=Path(tmp))
    set_config(cfg)
    init_engine(cfg.db_url)

    api_app = create_app(cfg)
    url = f"http://127.0.0.1:{port}"
    rprint(f"Serving bundle at {url}")

    if not no_browser:
        import threading, time
        def _open():
            time.sleep(1.5)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(api_app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    app()
