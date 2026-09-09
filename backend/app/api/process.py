"""
Guided geoprocessing tools. Each endpoint reads a registered dataset's raw
bytes, runs one well-scoped operation, then registers the result as a new
first-class dataset (origin="derived") with a ready-to-add layer -- so
outputs flow straight back into the same dataset/layer system as everything
else in the product (see spec section 10, "Derived Data").
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from fastapi import APIRouter

from app.geospatial import raster as raster_geo
from app.geospatial import vector as vector_geo
from app.processing import raster_calc, terrain, vector_ops
from app.schemas.dataset import DatasetKind, DatasetMetadata, DatasetOrigin
from app.schemas.layer import Layer
from app.schemas.process import (
    AspectRequest,
    BufferRequest,
    ClipRequest,
    HillshadeRequest,
    ProcessResult,
    RasterCalculatorRequest,
    RasterStatsRequest,
    ReprojectRequest,
    SlopeRequest,
)
from app.services import inspection, registry
from app.services.visualization import recommend_style
from app.storage import dataset_files
from app.utils.errors import DatasetNotFoundError

router = APIRouter(prefix="/process", tags=["process"])


def _load_dataset_and_bytes(dataset_id: str) -> tuple[DatasetMetadata, bytes, str]:
    dataset = registry.datasets.get(dataset_id)
    if not dataset:
        raise DatasetNotFoundError(dataset_id)
    suffix = f".{dataset.format}" if not dataset.format.startswith(".") else dataset.format
    data = dataset_files.load(dataset_id, suffix, derived=(dataset.origin == DatasetOrigin.derived))
    return dataset, data, suffix


def _register_derived_raster(name: str, data: bytes, tags: list[str], stats: dict, source_ids: list[str]) -> DatasetMetadata:
    meta_dict = inspection.inspect_bytes(data, f"{name}.tif", max_upload_mb=999)
    meta_dict["tags"] = sorted(set(meta_dict["tags"]) | set(tags))
    if stats:
        meta_dict.setdefault("style", {})
        meta_dict["style"]["min_value"] = stats.get("min")
        meta_dict["style"]["max_value"] = stats.get("max")
    dataset_id = registry.new_id("derived")
    dataset = DatasetMetadata(
        id=dataset_id,
        name=name,
        origin=DatasetOrigin.derived,
        source_ref={"derived_from": source_ids},
        **meta_dict,
    )
    registry.datasets.add(dataset.id, dataset)
    dataset_files.save(dataset_id, ".tif", data, derived=True)
    return dataset


def _register_derived_vector(name: str, gdf, tags: list[str], source_ids: list[str]) -> DatasetMetadata:
    import io

    buf = io.BytesIO()
    gdf.to_parquet(buf)
    data = buf.getvalue()
    meta_dict = inspection.inspect_bytes(data, f"{name}.parquet", max_upload_mb=999)
    meta_dict["tags"] = sorted(set(meta_dict["tags"]) | set(tags))
    dataset_id = registry.new_id("derived")
    dataset = DatasetMetadata(
        id=dataset_id,
        name=name,
        origin=DatasetOrigin.derived,
        source_ref={"derived_from": source_ids},
        **meta_dict,
    )
    registry.datasets.add(dataset.id, dataset)
    dataset_files.save(dataset_id, ".parquet", data, derived=True)
    return dataset


def _auto_layer(dataset: DatasetMetadata) -> Layer:
    rec = recommend_style(dataset)
    layer = Layer(
        id=registry.new_id("layer"),
        dataset_id=dataset.id,
        name=dataset.name,
        render_type=rec["render_type"],
        style=rec["style"],
        legend=rec.get("legend"),
        bbox=dataset.bbox,
    )
    registry.layers.add(layer.id, layer)
    return layer


@router.post("/hillshade", response_model=ProcessResult)
def process_hillshade(payload: HillshadeRequest):
    dataset, data, _ = _load_dataset_and_bytes(payload.dataset_id)
    result, stats = terrain.hillshade(data, payload.azimuth, payload.altitude, payload.z_factor)
    derived = _register_derived_raster(f"{dataset.name} - Hillshade", result, ["hillshade", "terrain"], stats, [dataset.id])
    _auto_layer(derived)
    return ProcessResult(dataset_id=derived.id, message=f"Hillshade created from '{dataset.name}'.")


@router.post("/slope", response_model=ProcessResult)
def process_slope(payload: SlopeRequest):
    dataset, data, _ = _load_dataset_and_bytes(payload.dataset_id)
    result, stats = terrain.slope(data, payload.units)
    derived = _register_derived_raster(f"{dataset.name} - Slope", result, ["slope", "terrain"], stats, [dataset.id])
    _auto_layer(derived)
    return ProcessResult(dataset_id=derived.id, message=f"Slope map created from '{dataset.name}'.")


@router.post("/aspect", response_model=ProcessResult)
def process_aspect(payload: AspectRequest):
    dataset, data, _ = _load_dataset_and_bytes(payload.dataset_id)
    result, stats = terrain.aspect(data)
    derived = _register_derived_raster(f"{dataset.name} - Aspect", result, ["aspect", "terrain"], stats, [dataset.id])
    _auto_layer(derived)
    return ProcessResult(dataset_id=derived.id, message=f"Aspect map created from '{dataset.name}'.")


@router.post("/buffer", response_model=ProcessResult)
def process_buffer(payload: BufferRequest):
    dataset, data, suffix = _load_dataset_and_bytes(payload.dataset_id)
    gdf = vector_geo.load_vector(data, f"x{suffix}")
    buffered = vector_ops.buffer(gdf, payload.distance_m)
    derived = _register_derived_vector(
        f"{dataset.name} - {int(payload.distance_m)}m Buffer", buffered, ["buffer"], [dataset.id]
    )
    _auto_layer(derived)
    return ProcessResult(dataset_id=derived.id, message=f"Buffered '{dataset.name}' by {payload.distance_m} m.")


@router.post("/clip", response_model=ProcessResult)
def process_clip(payload: ClipRequest):
    dataset, data, suffix = _load_dataset_and_bytes(payload.dataset_id)
    mask_dataset, mask_data, mask_suffix = _load_dataset_and_bytes(payload.mask_dataset_id)
    gdf = vector_geo.load_vector(data, f"x{suffix}")
    mask_gdf = vector_geo.load_vector(mask_data, f"x{mask_suffix}")
    clipped = vector_ops.clip(gdf, mask_gdf)
    derived = _register_derived_vector(
        f"{dataset.name} clipped to {mask_dataset.name}", clipped, ["clip"], [dataset.id, mask_dataset.id]
    )
    _auto_layer(derived)
    return ProcessResult(dataset_id=derived.id, message=f"Clipped '{dataset.name}' to '{mask_dataset.name}'.")


@router.post("/reproject", response_model=ProcessResult)
def process_reproject(payload: ReprojectRequest):
    dataset, data, suffix = _load_dataset_and_bytes(payload.dataset_id)
    gdf = vector_geo.load_vector(data, f"x{suffix}")
    reprojected = vector_ops.reproject(gdf, payload.target_crs)
    derived = _register_derived_vector(
        f"{dataset.name} ({payload.target_crs})", reprojected.to_crs("EPSG:4326"), ["reprojected"], [dataset.id]
    )
    _auto_layer(derived)
    return ProcessResult(dataset_id=derived.id, message=f"Reprojected '{dataset.name}' to {payload.target_crs}.")


@router.post("/raster-statistics")
def process_raster_stats(payload: RasterStatsRequest):
    dataset, data, _ = _load_dataset_and_bytes(payload.dataset_id)
    meta = raster_geo.extract_raster_metadata(data)
    return {"dataset_id": dataset.id, "stats": meta}


@router.post("/raster-calculator", response_model=ProcessResult)
def process_raster_calculator(payload: RasterCalculatorRequest):
    dataset_a, data_a, _ = _load_dataset_and_bytes(payload.dataset_a_id)
    with raster_geo.open_raster_bytes(data_a) as ds_a:
        profile = ds_a.profile.copy()
        arr_a = ds_a.read(1).astype("float32")

    arr_b = None
    source_ids = [dataset_a.id]
    if payload.dataset_b_id:
        dataset_b, data_b, _ = _load_dataset_and_bytes(payload.dataset_b_id)
        with raster_geo.open_raster_bytes(data_b) as ds_b:
            arr_b = ds_b.read(1).astype("float32")
        source_ids.append(dataset_b.id)
        if arr_b.shape != arr_a.shape:
            from app.utils.errors import ProcessingError

            raise ProcessingError(
                "Those two rasters don't line up.",
                hint="Raster calculator currently requires both rasters to share the same grid. "
                "Reproject/resample one of them to match first.",
            )

    result = raster_calc.evaluate(payload.expression, arr_a, arr_b)
    profile.update(dtype="float32", count=1)
    from rasterio.io import MemoryFile

    with MemoryFile() as memfile:
        with memfile.open(**profile) as dst:
            dst.write(np.nan_to_num(result, nan=0, posinf=0, neginf=0), 1)
        out_bytes = memfile.read()

    stats = {"min": float(np.nanmin(result)), "max": float(np.nanmax(result))}
    derived = _register_derived_raster(
        f"Calculator: {payload.expression}", out_bytes, ["raster-calculator"], stats, source_ids
    )
    _auto_layer(derived)
    return ProcessResult(dataset_id=derived.id, message=f"Computed '{payload.expression}'.")
