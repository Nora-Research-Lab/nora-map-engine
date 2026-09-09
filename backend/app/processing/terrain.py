"""
DEM-derived terrain products: hillshade, slope, aspect.

Implemented with plain numpy so there's no extra dependency beyond what
rasterio already pulls in. Inputs are capped to a maximum pixel dimension
before computation (`max_px`) to keep this safe to run on a 512MB instance;
for anything larger we say so rather than silently truncating without
explanation.
"""
from __future__ import annotations

import numpy as np
import rasterio
from rasterio.io import MemoryFile

from app.utils.errors import ProcessingError

MAX_TERRAIN_PX = 2000


def _read_dem(data: bytes) -> tuple[np.ndarray, dict]:
    with MemoryFile(data) as memfile:
        with memfile.open() as ds:
            if max(ds.width, ds.height) > MAX_TERRAIN_PX:
                raise ProcessingError(
                    "This elevation dataset is too large to process on the free tier.",
                    hint=f"Terrain tools are capped at {MAX_TERRAIN_PX}px per side here. "
                    "Downsample the DEM first, or run this on a larger instance.",
                )
            arr = ds.read(1).astype("float64")
            profile = ds.profile.copy()
            if ds.nodata is not None:
                arr = np.where(arr == ds.nodata, np.nan, arr)
            return arr, profile


def _cellsize(profile: dict) -> float:
    transform = profile["transform"]
    return abs(transform.a)


def hillshade(data: bytes, azimuth: float = 315, altitude: float = 45, z_factor: float = 1.0) -> tuple[bytes, dict]:
    arr, profile = _read_dem(data)
    cellsize = _cellsize(profile)

    dy, dx = np.gradient(arr * z_factor, cellsize)
    slope_rad = np.arctan(np.hypot(dx, dy))
    aspect_rad = np.arctan2(-dx, dy)

    az_rad = np.deg2rad(360.0 - azimuth + 90.0)
    alt_rad = np.deg2rad(altitude)

    shaded = (
        np.sin(alt_rad) * np.cos(slope_rad)
        + np.cos(alt_rad) * np.sin(slope_rad) * np.cos(az_rad - aspect_rad)
    )
    shaded = np.clip(shaded * 255, 0, 255).astype("uint8")

    out_profile = profile.copy()
    out_profile.update(dtype="uint8", count=1, nodata=None)
    return _write_single_band(shaded, out_profile), {"min": 0, "max": 255}


def slope(data: bytes, units: str = "degrees") -> tuple[bytes, dict]:
    arr, profile = _read_dem(data)
    cellsize = _cellsize(profile)
    dy, dx = np.gradient(arr, cellsize)
    rise_run = np.hypot(dx, dy)
    if units == "percent":
        result = rise_run * 100
    else:
        result = np.rad2deg(np.arctan(rise_run))
    out_profile = profile.copy()
    out_profile.update(dtype="float32", count=1)
    return _write_single_band(result.astype("float32"), out_profile), {
        "min": float(np.nanmin(result)),
        "max": float(np.nanmax(result)),
    }


def aspect(data: bytes) -> tuple[bytes, dict]:
    arr, profile = _read_dem(data)
    cellsize = _cellsize(profile)
    dy, dx = np.gradient(arr, cellsize)
    aspect_rad = np.arctan2(dy, -dx)
    aspect_deg = np.rad2deg(aspect_rad)
    aspect_deg = np.where(aspect_deg < 0, 90 - aspect_deg, np.where(aspect_deg > 90, 360 - aspect_deg + 90, 90 - aspect_deg))
    out_profile = profile.copy()
    out_profile.update(dtype="float32", count=1)
    return _write_single_band(aspect_deg.astype("float32"), out_profile), {"min": 0.0, "max": 360.0}


def _write_single_band(arr: np.ndarray, profile: dict) -> bytes:
    with MemoryFile() as memfile:
        with memfile.open(**profile) as ds:
            ds.write(np.nan_to_num(arr, nan=0), 1)
        return memfile.read()
