"""
Deterministic natural-language -> workflow router.

No LLM required. A person types something like "compare geology and
magnetic data" or "I want to see gold occurrences" and we map that to a
concrete, actionable suggestion: which datasets (from the library) look
relevant, and which workflow/tool to open.

This is intentionally simple and rule-based so it is fast, free to run, and
fully explainable -- and it's isolated behind `parse_intent()` so a future
version can swap in an LLM-backed router without touching any caller.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

ACTION_KEYWORDS: dict[str, list[str]] = {
    "compare": ["compare", "versus", "vs", "against", "side by side"],
    "overlay": ["overlay", "combine", "stack", "on top of"],
    "heatmap": ["heatmap", "heat map", "density", "hotspot", "hot spot"],
    "terrain": ["elevation", "terrain", "hillshade", "slope", "aspect", "relief"],
    "visualize": ["show", "see", "visualize", "display", "view", "look at"],
    "pattern": ["pattern", "cluster", "anomaly", "correlate", "overlap", "intersect"],
}

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "gold": ["gold", "au"],
    "mineral": ["mineral", "ore", "deposit", "prospectivity"],
    "geology": ["geology", "geological", "lithology", "rock", "formation"],
    "faults": ["fault", "faults", "tectonic", "structure"],
    "magnetic": ["magnetic", "magnetics", "aeromagnetic"],
    "gravity": ["gravity", "bouguer", "free-air", "free air"],
    "dem": ["dem", "elevation", "terrain", "topography"],
    "rivers": ["river", "rivers", "hydrology", "drainage", "basin"],
    "soil": ["soil", "soils"],
    "sediment": ["sediment", "sediments"],
    "petroleum": ["petroleum", "oil", "gas", "hydrocarbon"],
}

WORKFLOW_FOR_ACTION = {
    "compare": {"panel": "layers", "hint": "Add both datasets, then use opacity/order to compare them."},
    "overlay": {"panel": "layers", "hint": "Layer both datasets and adjust opacity to see how they relate."},
    "heatmap": {"panel": "tools", "tool": "heatmap", "hint": "We'll switch the point layer to a density heatmap."},
    "terrain": {"panel": "tools", "tool": "terrain", "hint": "Open the terrain tools to generate hillshade, slope, or aspect."},
    "visualize": {"panel": "datasets", "hint": "Pick a dataset below and add it to the map."},
    "pattern": {"panel": "layers", "hint": "Layer the related datasets and look for spatial overlap."},
}


@dataclass
class IntentResult:
    raw_text: str
    actions: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    panel: str = "datasets"
    tool: str | None = None
    hint: str = "Pick a dataset below and add it to the map."
    matched_tags: list[str] = field(default_factory=list)


def parse_intent(text: str) -> IntentResult:
    lowered = text.lower()
    actions = [a for a, kws in ACTION_KEYWORDS.items() if any(_contains(lowered, kw) for kw in kws)]
    domains = [d for d, kws in DOMAIN_KEYWORDS.items() if any(_contains(lowered, kw) for kw in kws)]

    primary_action = actions[0] if actions else ("compare" if len(domains) >= 2 else "visualize")
    workflow = WORKFLOW_FOR_ACTION.get(primary_action, WORKFLOW_FOR_ACTION["visualize"])

    return IntentResult(
        raw_text=text,
        actions=actions or [primary_action],
        domains=domains,
        panel=workflow["panel"],
        tool=workflow.get("tool"),
        hint=workflow["hint"],
        matched_tags=domains,
    )


def _contains(haystack: str, needle: str) -> bool:
    return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None
