"""
NORA Research Lab Hugging Face dataset catalog.

This module is what makes "every dataset we publish to Hugging Face shows up
in the Dataset Library automatically" true, including datasets that don't
exist yet. It does this by asking the Hugging Face Hub API for every dataset
repo under the `NoraResearchLab` org at request time (with a short cache),
rather than hard-coding a list.

A small ENRICHMENT table below gives nicer names/coverage/tags for the
datasets we know about today. Anything not in that table still shows up --
just with a name derived from its repo id and tags guessed from keywords in
that id -- so a brand-new repo appears in the library the next time the
cache refreshes, with zero code changes.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from huggingface_hub import HfApi

from app.config import get_settings
from app.schemas.dataset import DatasetKind, DatasetOrigin, DatasetSummary
from app.utils.errors import RemoteFetchError

# Known-good metadata for datasets published as of this writing. Anything the
# Hub returns that isn't listed here still appears in the catalog (see
# `_enrich` below) -- this table only makes the *known* entries a little nicer.
ENRICHMENT: dict[str, dict] = {
    "gem-global-active-faults": {
        "name": "Global Active Faults (GEM GAF-DB)",
        "tags": ["geology", "faults", "tectonic"],
        "coverage": "Global",
    },
    "world-petroleum-assessment-units": {
        "name": "World Petroleum Assessment Units",
        "tags": ["petroleum", "geology"],
        "coverage": "Global",
    },
    "Ilesha-Gold-Prospectivity-AME": {
        "name": "Ilesha Gold Prospectivity (AME)",
        "tags": ["gold", "mineral", "prospectivity"],
        "coverage": "Ilesha, Nigeria",
    },
    "Ilesha-Gold-Prospectivity-AME-prototype": {
        "name": "Ilesha Gold Prospectivity (prototype)",
        "tags": ["gold", "mineral", "prospectivity"],
        "coverage": "Ilesha, Nigeria",
    },
    "mineral-prospectivity-grid-na": {
        "name": "Mineral Prospectivity Grid (North America)",
        "tags": ["mineral", "prospectivity"],
        "coverage": "North America",
    },
    "ds424-geologic-map-north-america": {
        "name": "Geologic Map of North America (USGS DS-424)",
        "tags": ["geology"],
        "coverage": "North America",
    },
    "gplates-tectonic-intelligence": {
        "name": "GPlates Tectonic Intelligence",
        "tags": ["geology", "faults", "tectonic", "dem"],
        "coverage": "Global",
    },
    "glim-lithology-api-data": {
        "name": "Global Lithological Map (GLiM)",
        "tags": ["geology"],
        "coverage": "Global",
    },
    "Environmental_geology-landform": {
        "name": "Environmental Geology - Landform",
        "tags": ["environment", "terrain"],
        "coverage": "Global",
    },
    "Environmental_geology-roughness": {
        "name": "Environmental Geology - Terrain Roughness",
        "tags": ["environment", "terrain", "dem"],
        "coverage": "Global",
    },
    "Environmental_geology-aspect": {
        "name": "Environmental Geology - Aspect",
        "tags": ["environment", "terrain", "dem"],
        "coverage": "Global",
    },
    "Environmental_geology-slope": {
        "name": "Environmental Geology - Slope",
        "tags": ["environment", "terrain", "dem"],
        "coverage": "Global",
    },
    "Environmental_geology-dem": {
        "name": "Environmental Geology - DEM",
        "tags": ["environment", "terrain", "dem"],
        "coverage": "Global",
    },
    "Environmental_geology-datasets": {
        "name": "Environmental Geology - Combined Datasets",
        "tags": ["environment", "rivers", "geology"],
        "coverage": "Global",
    },
    "wgm2012-world-gravity-map": {
        "name": "World Gravity Map 2012 (WGM2012)",
        "tags": ["geophysics", "gravity"],
        "coverage": "Global",
    },
    "cmibs-critical-metals-black-shales": {
        "name": "Critical Metals in Black Shales (CMIBS)",
        "tags": ["geology", "mineral"],
        "coverage": "Global",
    },
    "ngdod-legacy-ore-deposits": {
        "name": "National Geochemical Database on Ore Deposits (NGDOD)",
        "tags": ["geology", "mineral"],
        "coverage": "United States",
    },
    "globsed-sediment-thickness": {
        "name": "Global Ocean Sediment Thickness (GlobSed)",
        "tags": ["sediment", "geology"],
        "coverage": "Global oceans",
    },
}

TAG_KEYWORDS = {
    "gold": "gold", "mineral": "mineral", "prospectivity": "mineral", "ore": "mineral",
    "geolog": "geology", "lithology": "geology", "fault": "faults", "tectonic": "faults",
    "magnetic": "geophysics", "gravity": "geophysics", "radiometric": "geophysics",
    "dem": "dem", "elevation": "dem", "slope": "terrain", "aspect": "terrain",
    "roughness": "terrain", "landform": "terrain",
    "river": "rivers", "basin": "rivers", "hydro": "rivers",
    "soil": "environment", "environment": "environment", "landcover": "environment",
    "sediment": "sediment", "petroleum": "petroleum", "oil": "petroleum", "gas": "petroleum",
}


@dataclass
class _CatalogCache:
    items: list[DatasetSummary] = field(default_factory=list)
    fetched_at: float = 0.0


_cache = _CatalogCache()


def _guess_tags(repo_id: str) -> list[str]:
    lowered = repo_id.lower()
    tags = {tag for kw, tag in TAG_KEYWORDS.items() if kw in lowered}
    return sorted(tags) or ["geoscience"]


def _friendly_name(repo_id: str) -> str:
    short = repo_id.split("/")[-1]
    return short.replace("-", " ").replace("_", " ").title()


def _enrich(repo_id: str, file_count: int) -> DatasetSummary:
    short = repo_id.split("/")[-1]
    known = ENRICHMENT.get(short, {})
    return DatasetSummary(
        id=f"hf:{repo_id}",
        name=known.get("name", _friendly_name(short)),
        kind=DatasetKind.vector,  # catalog entries are GeoParquet/tabular until materialized
        format="geoparquet",
        origin=DatasetOrigin.huggingface,
        coverage=known.get("coverage"),
        tags=known.get("tags") or _guess_tags(short),
        materialized=False,
        thumbnail_note=f"{file_count} file(s) on Hugging Face",
    )


def list_catalog_datasets(force_refresh: bool = False) -> list[DatasetSummary]:
    """List every dataset repo under the NORA Research Lab Hugging Face org.

    Cached in-process for `hf_catalog_cache_seconds` so a burst of Dataset
    Library page loads doesn't hammer the Hub API or slow down a cold start.
    """
    settings = get_settings()
    now = time.time()
    if not force_refresh and _cache.items and (now - _cache.fetched_at) < settings.hf_catalog_cache_seconds:
        return _cache.items

    api = HfApi(token=settings.hf_token)
    try:
        repos = list(api.list_datasets(author=settings.hf_org))
    except Exception as exc:  # network hiccup, org typo, rate limit, etc.
        if _cache.items:
            # Serve the stale cache rather than an empty library.
            return _cache.items
        raise RemoteFetchError(
            f"We couldn't reach Hugging Face to load the {settings.hf_org} dataset catalog."
        ) from exc

    items: list[DatasetSummary] = []
    for repo in repos:
        try:
            files = api.list_repo_files(repo_id=repo.id, repo_type="dataset")
        except Exception:
            files = []
        data_files = [f for f in files if f.endswith((".parquet", ".geoparquet", ".csv", ".geojson"))]
        items.append(_enrich(repo.id, len(data_files) or len(files)))

    _cache.items = items
    _cache.fetched_at = now
    return items


def find_catalog_dataset(repo_id: str) -> DatasetSummary | None:
    return next((d for d in list_catalog_datasets() if d.id == f"hf:{repo_id}"), None)


def list_repo_data_files(repo_id: str) -> list[str]:
    settings = get_settings()
    api = HfApi(token=settings.hf_token)
    try:
        files = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
    except Exception as exc:
        raise RemoteFetchError(f"We couldn't list files in the '{repo_id}' dataset.") from exc
    return [f for f in files if f.endswith((".parquet", ".geoparquet", ".csv", ".geojson"))]


def download_repo_file(repo_id: str, filename: str) -> bytes:
    from huggingface_hub import hf_hub_download

    settings = get_settings()
    try:
        path = hf_hub_download(repo_id=repo_id, filename=filename, repo_type="dataset", token=settings.hf_token)
    except Exception as exc:
        raise RemoteFetchError(f"We couldn't download '{filename}' from '{repo_id}'.") from exc
    with open(path, "rb") as fh:
        return fh.read()
