"""Runs once at startup: generates + registers the demo workspace."""
from __future__ import annotations

import logging

from app.config import get_settings
from app.demo.generate_demo_data import ensure_demo_data
from app.schemas.dataset import DatasetKind, DatasetMetadata, DatasetOrigin
from app.schemas.layer import Layer, LayerRenderType
from app.schemas.map import MapView, MapWorkspace
from app.services import inspection, registry
from app.services.visualization import recommend_style

logger = logging.getLogger(__name__)

DEMO_LABELS = {
    "gold_occurrences": ("Gold Occurrences", ["gold", "mineral"]),
    "faults": ("Faults", ["faults", "geology"]),
    "geology": ("Geological Units", ["geology"]),
    "dem": ("Elevation (DEM)", ["dem"]),
    "magnetic": ("Magnetic Intensity", ["geophysics", "magnetic"]),
}


def _register_demo_dataset(key: str, path) -> tuple[DatasetMetadata, Layer]:
    name, extra_tags = DEMO_LABELS[key]
    data = path.read_bytes()
    meta_dict = inspection.inspect_bytes(data, path.name, max_upload_mb=999)
    meta_dict["tags"] = sorted(set(meta_dict["tags"]) | set(extra_tags))

    dataset_id = f"demo_{key}"
    dataset = DatasetMetadata(
        id=dataset_id,
        name=name,
        origin=DatasetOrigin.demo,
        source_ref={"path": str(path)},
        **meta_dict,
    )
    registry.datasets.add(dataset.id, dataset)

    from app.storage import dataset_files

    dataset_files.save(dataset_id, path.suffix, data)

    rec = recommend_style(dataset)
    layer = Layer(
        id=registry.new_id("layer"),
        dataset_id=dataset.id,
        name=name,
        render_type=LayerRenderType(rec["render_type"]),
        style=rec["style"],
        legend=rec.get("legend"),
        bbox=dataset.bbox,
    )
    registry.layers.add(layer.id, layer)
    return dataset, layer


def bootstrap_demo_workspace() -> None:
    settings = get_settings()
    settings.ensure_dirs()
    try:
        paths = ensure_demo_data("./data/demo")
    except Exception:
        logger.exception("Failed to generate demo data; continuing without it.")
        return

    layer_ids = []
    for key in ("dem", "magnetic", "geology", "faults", "gold_occurrences"):
        try:
            _, layer = _register_demo_dataset(key, paths[key])
            layer_ids.append(layer.id)
        except Exception:
            logger.exception("Failed to register demo dataset '%s'", key)

    registry.load_persisted_workspaces()
    if not any(ws.name == "Gold Exploration Demo" for ws in registry.workspaces.list()):
        workspace = MapWorkspace(
            id=registry.new_id("map"),
            name="Gold Exploration Demo",
            description="Synthetic demo: gold occurrences, geology, faults, DEM, and magnetic data over a sample area.",
            view=MapView(center=[4.6, 7.65], zoom=10),
            layer_ids=layer_ids,
        )
        registry.workspaces.add(workspace.id, workspace)
        registry.persist_workspace(workspace)
