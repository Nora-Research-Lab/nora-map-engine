from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class MapView(BaseModel):
    center: list[float] = Field(default_factory=lambda: [8.6753, 9.0820])  # Nigeria-centered default
    zoom: float = 5.5
    bearing: float = 0
    pitch: float = 0


class MapWorkspaceCreate(BaseModel):
    name: str
    description: str | None = None
    view: MapView = Field(default_factory=MapView)
    layer_ids: list[str] = Field(default_factory=list)


class MapWorkspace(BaseModel):
    id: str
    name: str
    description: str | None = None
    view: MapView
    layer_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmbedConfig(BaseModel):
    """Configuration a parent site can pass to an embedded iframe via query string or postMessage."""

    center: list[float] | None = None
    zoom: float | None = None
    workspace_id: str | None = None
    dataset_ids: list[str] = Field(default_factory=list)
    theme: str = "dark"
    read_only: bool = False
    enabled_tools: list[str] | None = None


class ExportConfigResponse(BaseModel):
    workspace: MapWorkspace
    layers: list[dict[str, Any]]
    datasets: list[dict[str, Any]]
    share_url_path: str
