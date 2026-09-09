from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class DatasetKind(str, Enum):
    vector = "vector"
    raster = "raster"


class FieldType(str, Enum):
    numeric = "numeric"
    categorical = "categorical"
    text = "text"
    date = "date"


class FieldInfo(BaseModel):
    name: str
    type: FieldType
    min: float | None = None
    max: float | None = None
    unit: str | None = None
    distinct_values: list[str] | None = None
    missing_count: int = 0


class DatasetOrigin(str, Enum):
    upload = "upload"
    url = "url"
    huggingface = "huggingface"
    demo = "demo"
    derived = "derived"


class DatasetMetadata(BaseModel):
    """
    The canonical shape produced by automatic dataset inspection
    (app.services.inspection). This is what drives visualization
    recommendations and what the Dataset Library / Layer inspector show.
    """

    id: str
    name: str
    description: str | None = None
    kind: DatasetKind
    origin: DatasetOrigin = DatasetOrigin.upload
    format: str
    geometry_type: str | None = None  # Point | LineString | Polygon | Multi* (vector only)
    crs: str | None = None
    crs_confident: bool = True
    bbox: list[float] | None = None  # [minx, miny, maxx, maxy] in EPSG:4326
    feature_count: int | None = None  # vector
    width: int | None = None  # raster, px
    height: int | None = None  # raster, px
    band_count: int | None = None  # raster
    resolution: float | None = None  # raster, in CRS units (usually degrees or metres)
    nodata: float | None = None
    fields: list[FieldInfo] = Field(default_factory=list)
    size_bytes: int | None = None
    tags: list[str] = Field(default_factory=list)
    source_ref: dict[str, Any] = Field(default_factory=dict)
    recommended_preset: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # populated lazily, not always present in list views
    style: dict[str, Any] | None = None


class DatasetSummary(BaseModel):
    """Lightweight card shown in the Dataset Library -- cheap to list many of."""

    id: str
    name: str
    kind: DatasetKind
    format: str
    origin: DatasetOrigin
    coverage: str | None = None
    feature_count: int | None = None
    band_count: int | None = None
    resolution: float | None = None
    tags: list[str] = Field(default_factory=list)
    thumbnail_note: str | None = None
    materialized: bool = True  # False for catalog entries not yet added


class DatasetRegisterFromUrl(BaseModel):
    kind: Literal["url"] = "url"
    url: str
    name: str | None = None


class DatasetRegisterFromCatalog(BaseModel):
    kind: Literal["huggingface"] = "huggingface"
    repo_id: str
    filename: str
    name: str | None = None


class DatasetCreateResponse(BaseModel):
    dataset: DatasetMetadata
    warnings: list[str] = Field(default_factory=list)


class DatasetPreview(BaseModel):
    dataset_id: str
    kind: DatasetKind
    geojson: dict[str, Any] | None = None  # vector preview (subsampled)
    truncated: bool = False
    raster_preview_url: str | None = None  # PNG quicklook for raster
    stats: dict[str, Any] | None = None
