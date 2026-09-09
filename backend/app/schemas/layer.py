from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LayerRenderType(str, Enum):
    circle = "circle"          # points
    proportional_circle = "proportional_circle"
    cluster = "cluster"
    line = "line"
    fill = "fill"               # polygons, categorical or plain
    choropleth = "choropleth"   # polygons, numeric
    heatmap = "heatmap"
    raster = "raster"
    hillshade = "hillshade"


class LayerCreate(BaseModel):
    dataset_id: str
    name: str | None = None
    render_type: LayerRenderType | None = None  # None => use the dataset's recommended preset
    style_overrides: dict[str, Any] = Field(default_factory=dict)


class LayerUpdate(BaseModel):
    name: str | None = None
    visible: bool | None = None
    opacity: float | None = Field(default=None, ge=0, le=1)
    order: int | None = None
    render_type: LayerRenderType | None = None
    style_overrides: dict[str, Any] | None = None


class Layer(BaseModel):
    id: str
    dataset_id: str
    name: str
    render_type: LayerRenderType
    visible: bool = True
    opacity: float = 1.0
    order: int = 0
    style: dict[str, Any] = Field(default_factory=dict)
    legend: dict[str, Any] | None = None
    bbox: list[float] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
