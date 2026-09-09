"""
Turns raw dataset metadata into a concrete, ready-to-render layer style.

This is the piece of the product that lets a non-technical user skip GIS
styling entirely: given what `inspection.py` found, we pick a sensible
default here. Everything returned is plain data (MapLibre paint-property
shaped dicts) that the frontend applies directly -- no styling decisions
are made in the browser.
"""
from __future__ import annotations

from typing import Any

from app.schemas.dataset import DatasetMetadata, FieldType
from app.schemas.layer import LayerRenderType

# A small, colorblind-considerate categorical palette reused across the app.
CATEGORICAL_PALETTE = [
    "#C97C4A", "#4FB6B0", "#D9A441", "#7C93C9", "#8FA79C",
    "#B85C7A", "#5C9EAD", "#C9A24A", "#6B8F71", "#A46BC9",
]

NUMERIC_RAMP = ["#16324F", "#1B5E63", "#3B8C6E", "#8FBF6B", "#E8D25A", "#E8895A", "#C94A4A"]

DEM_PRESETS = ["elevation", "hillshade", "slope", "aspect"]

DOMAIN_PRESETS: dict[str, dict[str, Any]] = {
    "geology": {"palette": CATEGORICAL_PALETTE, "field_hint": ["unit", "lithology", "formation", "rock_type"]},
    "geophysics": {"ramp": NUMERIC_RAMP, "field_hint": ["mgal", "nt", "magnetic", "gravity"]},
    "terrain": {"dem_presets": DEM_PRESETS},
    "hydrology": {"color": "#4FB6B0"},
    "environment": {"palette": CATEGORICAL_PALETTE},
}


def _best_numeric_field(meta: DatasetMetadata) -> str | None:
    numeric = [f for f in meta.fields if f.type == FieldType.numeric]
    if not numeric:
        return None
    # Prefer a field whose name hints at the dataset's subject over an id/index column.
    ignore = {"id", "fid", "objectid", "index"}
    named = [f for f in numeric if f.name.lower() not in ignore]
    return (named or numeric)[0].name


def _best_categorical_field(meta: DatasetMetadata) -> str | None:
    cats = [f for f in meta.fields if f.type == FieldType.categorical]
    return cats[0].name if cats else None


def recommend_vector_style(meta: DatasetMetadata) -> dict[str, Any]:
    numeric_field = _best_numeric_field(meta)
    categorical_field = _best_categorical_field(meta)
    geom = (meta.geometry_type or "").lower()

    if "point" in geom:
        if meta.feature_count and meta.feature_count > 500:
            render_type = LayerRenderType.cluster
        elif numeric_field:
            render_type = LayerRenderType.proportional_circle
        else:
            render_type = LayerRenderType.circle
        style = {
            "color": CATEGORICAL_PALETTE[0],
            "radius": 5,
            "size_field": numeric_field,
            "color_field": categorical_field,
            "categorical_palette": CATEGORICAL_PALETTE if categorical_field else None,
        }
    elif "line" in geom:
        render_type = LayerRenderType.line
        style = {
            "color": "#4FB6B0",
            "width": 2,
            "width_field": numeric_field,
        }
    else:  # polygon / multipolygon / mixed
        if numeric_field:
            render_type = LayerRenderType.choropleth
            style = {"ramp": NUMERIC_RAMP, "field": numeric_field}
        else:
            render_type = LayerRenderType.fill
            style = {
                "color_field": categorical_field,
                "categorical_palette": CATEGORICAL_PALETTE if categorical_field else None,
                "fill_color": CATEGORICAL_PALETTE[0],
                "fill_opacity": 0.55,
                "outline_color": "#0E1512",
            }

    legend = _build_legend(render_type, style, meta)
    return {"render_type": render_type.value, "style": style, "legend": legend}


def recommend_raster_style(meta: DatasetMetadata) -> dict[str, Any]:
    tags = set(meta.tags)
    render_type = LayerRenderType.raster
    style: dict[str, Any] = {
        "ramp": NUMERIC_RAMP,
        "min": meta.style.get("min_value") if meta.style else None,
        "max": meta.style.get("max_value") if meta.style else None,
        "opacity": 0.85,
    }
    recommended_preset = None
    if "dem" in tags or "elevation" in tags:
        recommended_preset = "elevation"
        style["ramp"] = ["#1B5E63", "#3B8C6E", "#8FBF6B", "#E8D25A", "#C97C4A", "#7A4A2A", "#FFFFFF"]
    elif "magnetic" in tags or "gravity" in tags:
        recommended_preset = "geophysics"
        style["ramp"] = ["#16324F", "#4F6FA6", "#B0B0B0", "#D97757", "#7A2A0A"]
    legend = {"type": "gradient", "ramp": style["ramp"], "min": style.get("min"), "max": style.get("max")}
    return {
        "render_type": render_type.value,
        "style": style,
        "legend": legend,
        "recommended_preset": recommended_preset,
        "available_dem_presets": DEM_PRESETS if ("dem" in tags or "elevation" in tags) else None,
    }


def _build_legend(render_type: LayerRenderType, style: dict[str, Any], meta: DatasetMetadata) -> dict[str, Any]:
    if render_type in (LayerRenderType.choropleth,):
        field = style.get("field")
        f = next((f for f in meta.fields if f.name == field), None)
        return {"type": "gradient", "ramp": NUMERIC_RAMP, "field": field, "min": f.min if f else None, "max": f.max if f else None}
    if style.get("categorical_palette"):
        field = style.get("color_field")
        f = next((f for f in meta.fields if f.name == field), None)
        values = f.distinct_values if f else []
        return {
            "type": "categorical",
            "field": field,
            "entries": [
                {"value": v, "color": CATEGORICAL_PALETTE[i % len(CATEGORICAL_PALETTE)]}
                for i, v in enumerate(values or [])
            ],
        }
    return {"type": "single", "color": style.get("color") or style.get("fill_color") or CATEGORICAL_PALETTE[0]}


def recommend_style(meta: DatasetMetadata) -> dict[str, Any]:
    if meta.kind.value == "raster":
        return recommend_raster_style(meta)
    return recommend_vector_style(meta)
