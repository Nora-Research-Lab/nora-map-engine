"""
Dispatches an uploaded/fetched file to the right loader (vector or raster),
runs automatic metadata extraction, and tags the result so downstream
services (visualization, intent routing) understand what it is.
"""
from __future__ import annotations

from pathlib import Path

from app.geospatial import raster as raster_geo
from app.geospatial import vector as vector_geo
from app.schemas.dataset import DatasetKind, FieldInfo
from app.services.registry import new_id
from app.storage.huggingface_catalog import TAG_KEYWORDS
from app.utils.errors import DatasetTooLargeError, UnsupportedFormatError

SUPPORTED_VECTOR = sorted(vector_geo.VECTOR_EXTENSIONS)
SUPPORTED_RASTER = sorted(raster_geo.RASTER_EXTENSIONS)
UNSUPPORTED_BUT_PLANNED = {".nc", ".netcdf", ".zarr"}


def guess_kind(filename: str) -> DatasetKind:
    suffix = Path(filename).suffix.lower()
    if suffix in vector_geo.VECTOR_EXTENSIONS:
        return DatasetKind.vector
    if suffix in raster_geo.RASTER_EXTENSIONS:
        return DatasetKind.raster
    if suffix in UNSUPPORTED_BUT_PLANNED:
        raise UnsupportedFormatError(
            suffix, SUPPORTED_VECTOR + SUPPORTED_RASTER + ["(NetCDF/Zarr: architecture ready, not yet enabled)"]
        )
    raise UnsupportedFormatError(suffix or "unknown", SUPPORTED_VECTOR + SUPPORTED_RASTER)


def guess_tags(name: str, field_names: list[str]) -> list[str]:
    haystack = " ".join([name, *field_names]).lower()
    return sorted({tag for kw, tag in TAG_KEYWORDS.items() if kw in haystack}) or ["geoscience"]


def inspect_bytes(data: bytes, filename: str, max_upload_mb: int) -> dict:
    if len(data) > max_upload_mb * 1024 * 1024:
        raise DatasetTooLargeError(max_upload_mb)

    kind = guess_kind(filename)
    suffix = Path(filename).suffix.lower()

    if kind == DatasetKind.vector:
        gdf = vector_geo.load_vector(data, filename)
        meta = vector_geo.extract_vector_metadata(gdf)
        tags = guess_tags(filename, [f.name for f in meta["fields"]])
        return {
            "kind": kind,
            "format": suffix.lstrip("."),
            "size_bytes": len(data),
            "tags": tags,
            **meta,
        }

    raster_meta = raster_geo.extract_raster_metadata(data)
    tags = guess_tags(filename, [])
    if "dem" not in tags and any(k in filename.lower() for k in ("dem", "elevation", "elev")):
        tags.append("dem")
    return {
        "kind": kind,
        "format": suffix.lstrip("."),
        "size_bytes": len(data),
        "tags": tags,
        "geometry_type": None,
        "crs": raster_meta["crs"] or "EPSG:4326",
        "crs_confident": raster_meta["crs_confident"],
        "bbox": raster_meta["bbox"],
        "width": raster_meta["width"],
        "height": raster_meta["height"],
        "band_count": raster_meta["band_count"],
        "resolution": raster_meta["resolution"],
        "nodata": raster_meta["nodata"],
        "fields": [],
        "style": {"min_value": raster_meta["min_value"], "max_value": raster_meta["max_value"]},
    }
