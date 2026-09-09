"""
NORA Map Engine -- FastAPI application entrypoint.

On Render's free tier this single service does double duty: it serves the
JSON API under /api/*, and (once the frontend is built) serves the built
React app for every other route, so there's exactly one web service to
deploy, one URL to embed, and no cross-origin complexity by default.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import datasets, export, health, intent, layers, maps, process
from app.config import get_settings
from app.services.bootstrap import bootstrap_demo_workspace
from app.utils.errors import AppError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nora-map-engine")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    try:
        bootstrap_demo_workspace()
    except Exception:
        logger.exception("Demo workspace bootstrap failed; API still available.")
    yield


app = FastAPI(
    title=settings.app_name,
    description="Turn geological, environmental, geophysical, and terrain datasets into interactive maps.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
def handle_app_error(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception):
    logger.exception("Unhandled error while processing %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Something went wrong on our end.",
            "hint": "This has been logged. Please try again in a moment.",
        },
    )


for router in (health.router, datasets.router, layers.router, process.router, maps.router, export.router, intent.router):
    app.include_router(router, prefix=settings.api_prefix)


# --- Serve the built frontend (if present) ---------------------------------
_frontend_dir = (Path(__file__).parent / settings.frontend_dist_dir).resolve()

if _frontend_dir.exists():
    app.mount("/assets", StaticFiles(directory=_frontend_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        candidate = _frontend_dir / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_frontend_dir / "index.html")
else:
    @app.get("/")
    def frontend_not_built():
        return {
            "message": "NORA Map Engine API is running. The frontend hasn't been built yet.",
            "hint": "Run `npm run build` in /frontend, or use the API directly at /api/*.",
            "docs": "/docs",
        }
