"""
Generates small, realistic-looking synthetic datasets so the app is usable
the moment it starts -- no upload required. Deterministic (fixed seed) so
the same "Gold Exploration Demo" workspace appears every time.

Coverage area: a stand-in for Osun State, Nigeria, a real belt of
Nigeria's Ilesha Schist gold occurrences (see NORA Research Lab's
Ilesha Gold Prospectivity datasets on Hugging Face for the real thing).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

LON_MIN, LON_MAX = 4.35, 4.85
LAT_MIN, LAT_MAX = 7.45, 7.85

_RNG = np.random.default_rng(42)


def _points_geojson() -> dict:
    n = 180
    lons = _RNG.uniform(LON_MIN, LON_MAX, n)
    lats = _RNG.uniform(LAT_MIN, LAT_MAX, n)
    gold_ppm = np.round(_RNG.lognormal(mean=0.2, sigma=1.1, size=n), 3)
    host_rocks = _RNG.choice(["Schist", "Quartzite", "Granite", "Migmatite"], size=n, p=[0.4, 0.25, 0.2, 0.15])
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": {
                "name": f"Occurrence {i+1}",
                "gold_ppm": float(g),
                "host_rock": str(hr),
            },
        }
        for i, (lon, lat, g, hr) in enumerate(zip(lons, lats, gold_ppm, host_rocks))
    ]
    return {"type": "FeatureCollection", "features": features}


def _faults_geojson() -> dict:
    rng = _RNG
    lines = []
    for i in range(6):
        start = (rng.uniform(LON_MIN, LON_MAX), rng.uniform(LAT_MIN, LAT_MAX))
        angle = rng.uniform(0, np.pi)
        length = rng.uniform(0.15, 0.4)
        end = (start[0] + length * np.cos(angle), start[1] + length * np.sin(angle))
        lines.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [list(start), list(end)]},
                "properties": {"name": f"Fault {i+1}", "fault_type": rng.choice(["Normal", "Strike-slip", "Thrust"])},
            }
        )
    return {"type": "FeatureCollection", "features": lines}


def _geology_geojson() -> dict:
    units = ["Schist Belt", "Older Granite", "Migmatite-Gneiss", "Quartzite Ridge"]
    rng = _RNG
    cols = np.linspace(LON_MIN, LON_MAX, 3)
    rows = np.linspace(LAT_MIN, LAT_MAX, 3)
    features = []
    idx = 0
    for i in range(2):
        for j in range(2):
            x0, x1 = cols[i], cols[i + 1]
            y0, y1 = rows[j], rows[j + 1]
            jitter = rng.uniform(-0.02, 0.02, 4)
            poly = [
                [x0 + jitter[0], y0 + jitter[1]],
                [x1 + jitter[1], y0 + jitter[2]],
                [x1 + jitter[2], y1 + jitter[3]],
                [x0 + jitter[3], y1 + jitter[0]],
                [x0 + jitter[0], y0 + jitter[1]],
            ]
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [poly]},
                    "properties": {"unit": units[idx % len(units)], "age_ma": int(rng.uniform(500, 2500))},
                }
            )
            idx += 1
    return {"type": "FeatureCollection", "features": features}


def _smooth_field(shape: tuple[int, int], scale: float, seed_offset: int) -> np.ndarray:
    rng = np.random.default_rng(42 + seed_offset)
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    field = np.zeros(shape)
    for k in range(4):
        freq = (k + 1) * scale
        phase_x, phase_y = rng.uniform(0, 2 * np.pi, 2)
        field += np.sin(xx / w * freq * np.pi + phase_x) * np.cos(yy / h * freq * np.pi + phase_y) / (k + 1)
    field += rng.normal(0, 0.05, shape)
    return field


def _write_raster(path: Path, array: np.ndarray) -> None:
    h, w = array.shape
    transform = from_origin(LON_MIN, LAT_MAX, (LON_MAX - LON_MIN) / w, (LAT_MAX - LAT_MIN) / h)
    profile = {
        "driver": "GTiff",
        "height": h,
        "width": w,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array.astype("float32"), 1)


def _dem_array() -> np.ndarray:
    field = _smooth_field((200, 200), scale=3, seed_offset=1)
    normalized = (field - field.min()) / (field.max() - field.min())
    return 150 + normalized * 500  # metres, roughly hilly terrain


def _magnetic_array() -> np.ndarray:
    field = _smooth_field((200, 200), scale=6, seed_offset=2)
    normalized = (field - field.min()) / (field.max() - field.min())
    return -400 + normalized * 800  # nT anomaly, roughly realistic magnitude


def ensure_demo_data(data_dir: str) -> dict[str, Path]:
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)

    paths = {
        "gold_occurrences": root / "gold_occurrences.geojson",
        "faults": root / "faults.geojson",
        "geology": root / "geology.geojson",
        "dem": root / "dem.tif",
        "magnetic": root / "magnetic.tif",
    }

    if not paths["gold_occurrences"].exists():
        paths["gold_occurrences"].write_text(json.dumps(_points_geojson()))
    if not paths["faults"].exists():
        paths["faults"].write_text(json.dumps(_faults_geojson()))
    if not paths["geology"].exists():
        paths["geology"].write_text(json.dumps(_geology_geojson()))
    if not paths["dem"].exists():
        _write_raster(paths["dem"], _dem_array())
    if not paths["magnetic"].exists():
        _write_raster(paths["magnetic"], _magnetic_array())

    return paths
