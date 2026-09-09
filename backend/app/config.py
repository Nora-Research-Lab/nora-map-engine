"""
Central application configuration.

Everything that changes between local development and a Render deployment
lives here, driven by environment variables so no secrets or environment
assumptions are hard-coded anywhere else in the codebase.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General ---
    app_name: str = "NORA Map Engine"
    environment: str = "development"  # development | production
    api_prefix: str = "/api"

    # --- Networking / embedding ---
    # Comma-separated list of origins allowed to embed / call this service.
    # "*" is convenient for local dev but should be pinned to real domains in production.
    cors_origins: str = "*"

    # --- Storage ---
    # Render's filesystem is EPHEMERAL: anything written here disappears on
    # redeploy or when a free-tier instance spins down after idling. It is
    # only used as a scratch/cache area (uploaded files for the lifetime of
    # the running instance, temporary derived rasters, a local HF cache).
    # Swap `storage_backend` to "s3" or "supabase" once real persistence is
    # needed -- see app/storage/base.py.
    storage_backend: str = "local"
    local_storage_dir: str = "./data/uploads"
    derived_storage_dir: str = "./data/derived"
    workspace_storage_dir: str = "./data/workspaces"

    # --- Upload limits (protects the free-tier 512MB instance) ---
    max_upload_mb: int = 25
    max_preview_features: int = 2000
    max_raster_preview_px: int = 1024  # longest side used for stats/preview downsampling

    # --- Hugging Face dataset catalog ---
    # NORA Research Lab publishes its modernized geoscience datasets here.
    # New repos added to this org appear in the Dataset Library automatically
    # -- nothing in this codebase needs to change when a new dataset ships.
    hf_org: str = "NoraResearchLab"
    hf_catalog_cache_seconds: int = 6 * 60 * 60  # 6 hours
    hf_token: str | None = None  # only needed for private repos

    # --- Frontend ---
    # Path to the built frontend (Vite `dist`), resolved relative to
    # backend/app/ -- i.e. two levels up then into frontend/dist, which is
    # where it lives in this repo (and in the Docker image, which mirrors
    # the same backend/ + frontend/ sibling layout). When present, main.py
    # mounts it and serves the whole app (API + UI) from a single Render
    # service, which is the simplest topology on the free tier.
    frontend_dist_dir: str = "../../frontend/dist"

    # --- AGDFS integration (future) ---
    # See docs/AGDFS_INTEGRATION.md. Left blank by default; set this to
    # wire the Tools panel and Dataset Library up to a live AGDFS instance.
    agdfs_base_url: str | None = "https://agdfs.onrender.com"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        for d in (self.local_storage_dir, self.derived_storage_dir, self.workspace_storage_dir):
            Path(d).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
