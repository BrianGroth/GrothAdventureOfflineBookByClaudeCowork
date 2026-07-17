"""FastAPI application factory."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from core.config import AppConfig
from core.db.session import init_engine
from core.api.routers import entries, media, search, tags, stats, book


def create_app(cfg: AppConfig) -> FastAPI:
    """Create and configure the FastAPI application."""
    init_engine(cfg.db_url)

    app = FastAPI(
        title="Groth Adventures Scrapbook",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store config on app state
    app.state.cfg = cfg

    # Register API routers
    app.include_router(entries.router, prefix="/api")
    app.include_router(media.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(tags.router, prefix="/api")
    app.include_router(stats.router, prefix="/api")
    app.include_router(book.router, prefix="/api")

    # Serve built React app if dist exists
    dist_dir = Path(__file__).parent.parent.parent / "app" / "dist"
    if dist_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")

        @app.get("/", include_in_schema=False)
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str = ""):
            if full_path.startswith("api/"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            index = dist_dir / "index.html"
            if index.exists():
                # index.html must never be cached: built assets are hash-named,
                # so a stale index would point at assets that no longer exist.
                return FileResponse(str(index), headers={"Cache-Control": "no-cache"})
            return {"message": "Build the React app with: cd app && npm run build"}
    else:
        @app.get("/", include_in_schema=False)
        async def root():
            return {
                "message": "Groth Adventures Scrapbook API",
                "docs": "/api/docs",
                "note": "Run 'cd app && npm install && npm run build' to enable the web UI",
            }

    return app
