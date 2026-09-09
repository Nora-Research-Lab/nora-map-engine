from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.schemas.dataset import DatasetKind, DatasetOrigin
from app.schemas.map import ExportConfigResponse
from app.services import registry
from app.storage import dataset_files
from app.utils.errors import DatasetNotFoundError, MapNotFoundError

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/config/{map_id}", response_model=ExportConfigResponse)
def export_config(map_id: str):
    workspace = registry.workspaces.get(map_id)
    if not workspace:
        raise MapNotFoundError(map_id)

    layers = [registry.layers.get(lid) for lid in workspace.layer_ids]
    layers = [l for l in layers if l]
    dataset_ids = {l.dataset_id for l in layers}
    datasets = [registry.datasets.get(did) for did in dataset_ids]
    datasets = [d for d in datasets if d]

    return ExportConfigResponse(
        workspace=workspace,
        layers=[l.model_dump(mode="json") for l in layers],
        datasets=[d.model_dump(mode="json") for d in datasets],
        share_url_path=f"/map?workspace={map_id}",
    )


@router.get("/dataset/{dataset_id}.geojson")
def export_geojson(dataset_id: str):
    dataset = registry.datasets.get(dataset_id)
    if not dataset or dataset.kind != DatasetKind.vector:
        raise DatasetNotFoundError(dataset_id)
    from app.geospatial import vector as vector_geo

    suffix = f".{dataset.format}" if not dataset.format.startswith(".") else dataset.format
    data = dataset_files.load(dataset_id, suffix, derived=(dataset.origin == DatasetOrigin.derived))
    gdf = vector_geo.load_vector(data, f"x{suffix}")
    geojson = gdf.to_json()
    return Response(
        content=geojson,
        media_type="application/geo+json",
        headers={"Content-Disposition": f'attachment; filename="{dataset.name}.geojson"'},
    )


@router.get("/dataset/{dataset_id}.tif")
def export_geotiff(dataset_id: str):
    dataset = registry.datasets.get(dataset_id)
    if not dataset or dataset.kind != DatasetKind.raster:
        raise DatasetNotFoundError(dataset_id)
    suffix = f".{dataset.format}" if not dataset.format.startswith(".") else dataset.format
    data = dataset_files.load(dataset_id, suffix, derived=(dataset.origin == DatasetOrigin.derived))
    return Response(
        content=data,
        media_type="image/tiff",
        headers={"Content-Disposition": f'attachment; filename="{dataset.name}.tif"'},
    )
