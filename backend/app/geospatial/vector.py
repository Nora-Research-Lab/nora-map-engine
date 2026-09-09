"""
Vector dataset loading + metadata extraction.

Everything here works on an in-memory GeoDataFrame so the same code path
serves uploads, URL-registered datasets, and Hugging Face catalog datasets.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from app.schemas.dataset import FieldInfo, FieldType
from app.utils.errors import InvalidDatasetError, NoCoordinatesError

LAT_NAMES = {"lat", "latitude", "y"}
LON_NAMES = {"lon", "lng", "long", "longitude", "x"}

VECTOR_EXTENSIONS = {".geojson", ".json", ".gpkg", ".parquet", ".geoparquet", ".zip", ".csv"}


def _find_latlon_columns(columns: list[str]) -> tuple[str, str] | None:
    lower = {c.lower(): c for c in columns}
    lat = next((lower[c] for c in LAT_NAMES if c in lower), None)
    lon = next((lower[c] for c in LON_NAMES if c in lower), None)
    if lat and lon:
        return lat, lon
    return None


def load_csv(data: bytes) -> gpd.GeoDataFrame:
    df = pd.read_csv(io.BytesIO(data))
    match = _find_latlon_columns(list(df.columns))
    if not match:
        raise NoCoordinatesError()
    lat_col, lon_col = match
    df = df.dropna(subset=[lat_col, lon_col])
    if df.empty:
        raise NoCoordinatesError()
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs="EPSG:4326",
    )
    return gdf


def load_geojson(data: bytes) -> gpd.GeoDataFrame:
    try:
        obj = json.loads(data)
    except json.JSONDecodeError as exc:
        raise InvalidDatasetError("That file isn't valid GeoJSON (couldn't parse it as JSON).") from exc
    if not obj.get("type"):
        raise InvalidDatasetError()
    gdf = gpd.GeoDataFrame.from_features(obj.get("features", obj), crs="EPSG:4326")
    if gdf.empty:
        raise InvalidDatasetError("That GeoJSON file doesn't contain any features.")
    return gdf


def load_geopackage_or_shapefile(data: bytes, filename: str) -> gpd.GeoDataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix == ".zip":
        # Expect a zipped Shapefile (.shp/.dbf/.shx/.prj bundled together)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            shp_names = [n for n in zf.namelist() if n.lower().endswith(".shp")]
            if not shp_names:
                raise InvalidDatasetError(
                    "That zip file doesn't contain a Shapefile (.shp/.dbf/.shx)."
                )
        gdf = gpd.read_file(f"zip://{_write_temp(data, filename)}")
    else:
        gdf = gpd.read_file(io.BytesIO(data))
    if gdf.empty:
        raise InvalidDatasetError()
    return gdf


def load_geoparquet(data: bytes) -> gpd.GeoDataFrame:
    gdf = gpd.read_parquet(io.BytesIO(data))
    if gdf.empty:
        raise InvalidDatasetError("That GeoParquet file doesn't contain any rows.")
    return gdf


def _write_temp(data: bytes, filename: str) -> str:
    import tempfile

    tmp_dir = Path(tempfile.mkdtemp(prefix="nora-map-"))
    tmp_path = tmp_dir / Path(filename).name
    tmp_path.write_bytes(data)
    return str(tmp_path)


def load_vector(data: bytes, filename: str) -> gpd.GeoDataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return load_csv(data)
    if suffix in (".geojson", ".json"):
        return load_geojson(data)
    if suffix in (".parquet", ".geoparquet"):
        return load_geoparquet(data)
    if suffix in (".gpkg", ".zip"):
        return load_geopackage_or_shapefile(data, filename)
    raise InvalidDatasetError(f"Unrecognized vector format '{suffix or 'unknown'}'.")


def _classify_field(series: pd.Series) -> FieldInfo:
    missing = int(series.isna().sum())
    non_null = series.dropna()
    if pd.api.types.is_numeric_dtype(series):
        if non_null.empty:
            return FieldInfo(name=series.name, type=FieldType.numeric, missing_count=missing)
        return FieldInfo(
            name=series.name,
            type=FieldType.numeric,
            min=float(non_null.min()),
            max=float(non_null.max()),
            missing_count=missing,
        )
    distinct = non_null.astype(str).unique().tolist()
    if len(distinct) <= 30:
        return FieldInfo(
            name=series.name,
            type=FieldType.categorical,
            distinct_values=sorted(distinct)[:30],
            missing_count=missing,
        )
    return FieldInfo(name=series.name, type=FieldType.text, missing_count=missing)


def extract_vector_metadata(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    crs_confident = gdf.crs is not None
    if not crs_confident:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    working = gdf if gdf.crs and gdf.crs.to_epsg() == 4326 else gdf.to_crs("EPSG:4326")

    bounds = working.total_bounds  # minx, miny, maxx, maxy
    geom_types = working.geom_type.dropna().unique().tolist()
    geometry_type = geom_types[0] if len(geom_types) == 1 else "Mixed"

    fields = [
        _classify_field(working[col])
        for col in working.columns
        if col != working.geometry.name
    ]

    return {
        "geometry_type": geometry_type,
        "crs": "EPSG:4326",
        "crs_confident": crs_confident,
        "bbox": [float(b) for b in bounds],
        "feature_count": int(len(working)),
        "fields": fields,
    }


def to_preview_geojson(gdf: gpd.GeoDataFrame, limit: int) -> tuple[dict[str, Any], bool]:
    """Subsample large datasets so the browser never receives millions of features."""
    truncated = False
    working = gdf
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        working = gdf.to_crs("EPSG:4326")
    if len(working) > limit:
        working = working.sample(n=limit, random_state=42)
        truncated = True
    geojson = json.loads(working.to_json())
    return geojson, truncated
