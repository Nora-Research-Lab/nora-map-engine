"""
Raster dataset loading + metadata extraction.

Memory-conscious by construction: stats and previews are always computed on
a downsampled read (`out_shape`), never on the full-resolution array, which
matters a great deal on a 512MB Render free-tier instance.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.io import MemoryFile

from app.utils.errors import EmptyRasterError, InvalidDatasetError

RASTER_EXTENSIONS = {".tif", ".tiff", ".cog"}


def _downsampled_read(dataset: rasterio.DatasetReader, max_px: int) -> np.ndarray:
    scale = max(dataset.width, dataset.height) / max_px
    if scale <= 1:
        out_shape = (dataset.count, dataset.height, dataset.width)
    else:
        out_shape = (
            dataset.count,
            max(1, int(dataset.height / scale)),
            max(1, int(dataset.width / scale)),
        )
    return dataset.read(out_shape=out_shape, resampling=Resampling.average)


def is_cog(dataset: rasterio.DatasetReader) -> bool:
    # A practical (not exhaustive) COG check: internal tiling + overviews present.
    try:
        block_shapes = dataset.block_shapes
        tiled = all(bs[0] not in (dataset.height,) for bs in block_shapes) if block_shapes else False
        has_overviews = any(dataset.overviews(i) for i in range(1, dataset.count + 1))
        return bool(tiled and has_overviews)
    except Exception:
        return False


def open_raster_bytes(data: bytes):
    return MemoryFile(data).open()


def extract_raster_metadata(data: bytes, max_preview_px: int = 1024) -> dict[str, Any]:
    try:
        with MemoryFile(data) as memfile:
            with memfile.open() as ds:
                if ds.count == 0 or ds.width == 0 or ds.height == 0:
                    raise InvalidDatasetError("That raster file doesn't contain any bands or pixels.")

                arr = _downsampled_read(ds, max_preview_px)
                nodata = ds.nodata
                if nodata is not None:
                    mask = arr != nodata
                    valid = arr[mask]
                else:
                    valid = arr[np.isfinite(arr)]

                if valid.size == 0:
                    raise EmptyRasterError()

                bounds = ds.bounds
                crs = ds.crs.to_string() if ds.crs else None
                bbox_4326 = None
                if ds.crs:
                    from rasterio.warp import transform_bounds

                    try:
                        bbox_4326 = list(
                            transform_bounds(ds.crs, "EPSG:4326", *bounds, densify_pts=21)
                        )
                    except Exception:
                        bbox_4326 = None

                return {
                    "width": ds.width,
                    "height": ds.height,
                    "band_count": ds.count,
                    "crs": crs,
                    "crs_confident": ds.crs is not None,
                    "bbox": bbox_4326 or [bounds.left, bounds.bottom, bounds.right, bounds.top],
                    "resolution": float(abs(ds.res[0])),
                    "nodata": float(nodata) if nodata is not None else None,
                    "min_value": float(np.nanmin(valid)),
                    "max_value": float(np.nanmax(valid)),
                    "is_cog": is_cog(ds),
                }
    except rasterio.errors.RasterioIOError as exc:
        raise InvalidDatasetError(
            "We couldn't open that as a raster file. Is it a valid GeoTIFF?"
        ) from exc


_VIRIDIS_STOPS = np.array(
    [
        [68, 1, 84], [72, 40, 120], [62, 74, 137], [49, 104, 142],
        [38, 130, 142], [31, 158, 137], [53, 183, 121], [109, 205, 89],
        [180, 222, 44], [253, 231, 37],
    ],
    dtype=np.float64,
)


def _apply_viridis(normalized: np.ndarray) -> np.ndarray:
    """Cheap colormap lookup so we don't need matplotlib just for a thumbnail."""
    idx = np.clip((normalized * (len(_VIRIDIS_STOPS) - 1)).astype(int), 0, len(_VIRIDIS_STOPS) - 1)
    return _VIRIDIS_STOPS[idx].astype(np.uint8)


def raster_quicklook_png(data: bytes, max_px: int = 512) -> bytes:
    """Render a small PNG quicklook for the Dataset Library / layer thumbnail.

    Uses Pillow + a hand-rolled viridis lookup instead of matplotlib, which
    keeps the dependency footprint (and cold-start memory) much smaller --
    matters on Render's free tier.
    """
    from PIL import Image

    with MemoryFile(data) as memfile:
        with memfile.open() as ds:
            arr = _downsampled_read(ds, max_px)[0].astype(np.float64)
            nodata = ds.nodata

    mask = arr == nodata if nodata is not None else ~np.isfinite(arr)
    valid = arr[~mask]
    if valid.size == 0:
        raise EmptyRasterError()

    lo, hi = np.percentile(valid, [2, 98])
    if hi <= lo:
        hi = lo + 1
    normalized = np.clip((arr - lo) / (hi - lo), 0, 1)
    rgb = _apply_viridis(normalized)

    alpha = np.where(mask, 0, 255).astype(np.uint8)
    rgba = np.dstack([rgb, alpha])
    img = Image.fromarray(rgba, mode="RGBA")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
