from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import Response

from app.config import get_settings
from app.schemas.dataset import (
    DatasetCreateResponse,
    DatasetKind,
    DatasetMetadata,
    DatasetOrigin,
    DatasetPreview,
    DatasetRegisterFromCatalog,
    DatasetRegisterFromUrl,
    DatasetSummary,
)
from app.services import inspection, registry
from app.services.visualization import recommend_style
from app.storage import dataset_files, huggingface_catalog
from app.storage.url import fetch_url
from app.utils.errors import DatasetNotFoundError, DatasetTooLargeError

router = APIRouter(prefix="/datasets", tags=["datasets"])

MAX_CATALOG_DOWNLOAD_MB = 80


def _to_summary(d: DatasetMetadata) -> DatasetSummary:
    coverage = None
    if d.bbox:
        coverage = f"{d.bbox[1]:.2f}, {d.bbox[0]:.2f} to {d.bbox[3]:.2f}, {d.bbox[2]:.2f}"
    return DatasetSummary(
        id=d.id,
        name=d.name,
        kind=d.kind,
        format=d.format,
        origin=d.origin,
        coverage=coverage,
        feature_count=d.feature_count,
        band_count=d.band_count,
        resolution=d.resolution,
        tags=d.tags,
        materialized=True,
    )


def _register(name: str, filename: str, data: bytes, origin: DatasetOrigin, source_ref: dict) -> DatasetMetadata:
    settings = get_settings()
    limit = settings.max_upload_mb if origin != DatasetOrigin.huggingface else MAX_CATALOG_DOWNLOAD_MB
    meta_dict = inspection.inspect_bytes(data, filename, max_upload_mb=limit)

    dataset_id = registry.new_id("ds")
    dataset = DatasetMetadata(
        id=dataset_id,
        name=name or Path(filename).stem.replace("_", " ").title(),
        origin=origin,
        source_ref=source_ref,
        **meta_dict,
    )
    registry.datasets.add(dataset.id, dataset)
    dataset_files.save(dataset_id, Path(filename).suffix.lower(), data)
    return dataset


@router.post("", response_model=DatasetCreateResponse)
async def upload_dataset(file: UploadFile = File(...)):
    data = await file.read()
    settings = get_settings()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise DatasetTooLargeError(settings.max_upload_mb)
    dataset = _register(
        name=Path(file.filename).stem,
        filename=file.filename,
        data=data,
        origin=DatasetOrigin.upload,
        source_ref={"original_filename": file.filename},
    )
    return DatasetCreateResponse(dataset=dataset)


@router.post("/url", response_model=DatasetCreateResponse)
def register_from_url(payload: DatasetRegisterFromUrl):
    data = fetch_url(payload.url)
    filename = payload.url.split("?")[0].split("/")[-1] or "dataset"
    dataset = _register(
        name=payload.name or Path(filename).stem,
        filename=filename,
        data=data,
        origin=DatasetOrigin.url,
        source_ref={"url": payload.url},
    )
    return DatasetCreateResponse(dataset=dataset)


@router.post("/catalog/add", response_model=DatasetCreateResponse)
def add_from_catalog(payload: DatasetRegisterFromCatalog):
    data = huggingface_catalog.download_repo_file(payload.repo_id, payload.filename)
    dataset = _register(
        name=payload.name or Path(payload.filename).stem,
        filename=payload.filename,
        data=data,
        origin=DatasetOrigin.huggingface,
        source_ref={"repo_id": payload.repo_id, "filename": payload.filename},
    )
    return DatasetCreateResponse(dataset=dataset)


@router.get("/catalog", response_model=list[DatasetSummary])
def list_catalog(refresh: bool = False):
    """Every dataset published under the NORA Research Lab Hugging Face org --
    including ones added after this service was deployed."""
    return huggingface_catalog.list_catalog_datasets(force_refresh=refresh)


@router.get("/catalog/{repo_id:path}/files")
def list_catalog_files(repo_id: str):
    return {"repo_id": repo_id, "files": huggingface_catalog.list_repo_data_files(repo_id)}


@router.get("", response_model=list[DatasetSummary])
def list_datasets(include_catalog: bool = Query(False)):
    items = [_to_summary(d) for d in registry.datasets.list()]
    if include_catalog:
        items.extend(huggingface_catalog.list_catalog_datasets())
    return items


@router.get("/{dataset_id}", response_model=DatasetMetadata)
def get_dataset(dataset_id: str):
    dataset = registry.datasets.get(dataset_id)
    if not dataset:
        raise DatasetNotFoundError(dataset_id)
    return dataset


@router.get("/{dataset_id}/metadata", response_model=DatasetMetadata)
def get_dataset_metadata(dataset_id: str):
    return get_dataset(dataset_id)


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
def preview_dataset(dataset_id: str):
    dataset = registry.datasets.get(dataset_id)
    if not dataset:
        raise DatasetNotFoundError(dataset_id)
    settings = get_settings()
    suffix = f".{dataset.format}" if not dataset.format.startswith(".") else dataset.format

    if dataset.kind == DatasetKind.vector:
        from app.geospatial import vector as vector_geo

        data = dataset_files.load(dataset_id, suffix, derived=(dataset.origin == DatasetOrigin.derived))
        gdf = vector_geo.load_vector(data, f"x{suffix}")
        geojson, truncated = vector_geo.to_preview_geojson(gdf, settings.max_preview_features)
        return DatasetPreview(dataset_id=dataset_id, kind=dataset.kind, geojson=geojson, truncated=truncated)

    return DatasetPreview(
        dataset_id=dataset_id,
        kind=dataset.kind,
        raster_preview_url=f"/api/datasets/{dataset_id}/thumbnail.png",
        stats={"min": dataset.style.get("min_value") if dataset.style else None,
               "max": dataset.style.get("max_value") if dataset.style else None},
    )


@router.get("/{dataset_id}/thumbnail.png")
def dataset_thumbnail(dataset_id: str):
    dataset = registry.datasets.get(dataset_id)
    if not dataset or dataset.kind != DatasetKind.raster:
        raise DatasetNotFoundError(dataset_id)
    from app.geospatial import raster as raster_geo

    suffix = f".{dataset.format}" if not dataset.format.startswith(".") else dataset.format
    data = dataset_files.load(dataset_id, suffix, derived=(dataset.origin == DatasetOrigin.derived))
    png = raster_geo.raster_quicklook_png(data)
    return Response(content=png, media_type="image/png")


@router.get("/{dataset_id}/style")
def dataset_style(dataset_id: str):
    dataset = registry.datasets.get(dataset_id)
    if not dataset:
        raise DatasetNotFoundError(dataset_id)
    return recommend_style(dataset)


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str):
    if not registry.datasets.get(dataset_id):
        raise DatasetNotFoundError(dataset_id)
    registry.datasets.delete(dataset_id)
    for layer in [l for l in registry.layers.list() if l.dataset_id == dataset_id]:
        registry.layers.delete(layer.id)
    return {"deleted": dataset_id}
