from __future__ import annotations

from fastapi import APIRouter

from app.schemas.layer import Layer, LayerCreate, LayerUpdate
from app.services import registry
from app.services.visualization import recommend_style
from app.utils.errors import DatasetNotFoundError, LayerNotFoundError

router = APIRouter(prefix="/layers", tags=["layers"])


@router.get("", response_model=list[Layer])
def list_layers():
    return sorted(registry.layers.list(), key=lambda l: l.order)


@router.post("", response_model=Layer)
def create_layer(payload: LayerCreate):
    dataset = registry.datasets.get(payload.dataset_id)
    if not dataset:
        raise DatasetNotFoundError(payload.dataset_id)

    rec = recommend_style(dataset)
    render_type = payload.render_type.value if payload.render_type else rec["render_type"]
    style = {**rec["style"], **payload.style_overrides}

    existing_orders = [l.order for l in registry.layers.list()]
    layer = Layer(
        id=registry.new_id("layer"),
        dataset_id=dataset.id,
        name=payload.name or dataset.name,
        render_type=render_type,
        style=style,
        legend=rec.get("legend"),
        bbox=dataset.bbox,
        order=(max(existing_orders) + 1) if existing_orders else 0,
    )
    registry.layers.add(layer.id, layer)
    return layer


@router.get("/{layer_id}", response_model=Layer)
def get_layer(layer_id: str):
    layer = registry.layers.get(layer_id)
    if not layer:
        raise LayerNotFoundError(layer_id)
    return layer


@router.patch("/{layer_id}", response_model=Layer)
def update_layer(layer_id: str, payload: LayerUpdate):
    layer = registry.layers.get(layer_id)
    if not layer:
        raise LayerNotFoundError(layer_id)
    updated = layer.model_copy(update={k: v for k, v in payload.model_dump(exclude_unset=True).items()})
    if payload.style_overrides is not None:
        updated.style = {**layer.style, **payload.style_overrides}
    registry.layers.update(layer_id, updated)
    return updated


@router.delete("/{layer_id}")
def delete_layer(layer_id: str):
    if not registry.layers.get(layer_id):
        raise LayerNotFoundError(layer_id)
    registry.layers.delete(layer_id)
    return {"deleted": layer_id}
