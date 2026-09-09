"""Vector geoprocessing: buffer, clip, reproject."""
from __future__ import annotations

import geopandas as gpd

from app.utils.errors import ProcessingError


def buffer(gdf: gpd.GeoDataFrame, distance_m: float) -> gpd.GeoDataFrame:
    # Buffering in metres requires a projected CRS; reproject to a suitable
    # equal-area/metric CRS, buffer, then bring the result back to WGS84.
    metric = gdf.to_crs(gdf.estimate_utm_crs()) if gdf.crs and gdf.crs.is_geographic else gdf
    buffered = metric.copy()
    buffered["geometry"] = metric.geometry.buffer(distance_m)
    return buffered.to_crs("EPSG:4326")


def clip(gdf: gpd.GeoDataFrame, mask_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    try:
        return gpd.clip(gdf, mask_gdf.to_crs(gdf.crs))
    except Exception as exc:
        raise ProcessingError(
            "We couldn't clip that dataset.",
            hint="Make sure both datasets actually overlap spatially.",
        ) from exc


def reproject(gdf: gpd.GeoDataFrame, target_crs: str) -> gpd.GeoDataFrame:
    try:
        return gdf.to_crs(target_crs)
    except Exception as exc:
        raise ProcessingError(f"We couldn't reproject to '{target_crs}'.") from exc
