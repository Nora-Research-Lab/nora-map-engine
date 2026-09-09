# NORA Map Engine

Turn geological, environmental, geophysical, satellite, and terrain
datasets into interactive maps -- without needing to know GIS, coordinate
systems, raster formats, or MapLibre. Built to run as a single, embeddable
web service on Render's free tier.

A person adds a dataset (upload, a public URL, or one click from the
built-in Hugging Face library); the service inspects it, figures out what
kind of data it is, and recommends how it should look; the person adds it
to the map, layers in more data, runs a guided tool (hillshade, buffer,
raster calculator, ...), and exports or shares the result. No GIS
configuration screens anywhere.

```
"I want to see gold occurrences"        -> matches the library, adds a point layer
"Compare geology and magnetic data"     -> opens Layers with both suggested
"Visualize elevation"                   -> opens Tools -> Terrain
```

---

## Contents

- [What's actually implemented](#whats-actually-implemented)
- [Project tree](#project-tree)
- [How the pieces fit together](#how-the-pieces-fit-together)
- [Local setup](#local-setup)
- [Deploying to Render](#deploying-to-render)
- [Environment variables](#environment-variables)
- [Example API requests](#example-api-requests)
- [Embedding in another site](#embedding-in-another-site)
- [Extending the system](#extending-the-system)
- [Connecting to AGDFS](#connecting-to-agdfs)
- [Connecting AI/ML models](#connecting-aiml-models)
- [Known limitations (read before you rely on this in production)](#known-limitations)

---

## What's actually implemented

This ships a working foundation, not a mockup -- every piece below was
built, installed, and exercised against real requests before being
included here (see [Known limitations](#known-limitations) for what's
intentionally out of scope for v1).

| Area | Status |
|---|---|
| Upload & inspect GeoJSON, CSV (lat/lon), GeoPackage, zipped Shapefile, GeoParquet, GeoTIFF/COG | ✅ working |
| Automatic visualization recommendation (points/lines/polygons/rasters, DEM presets) | ✅ working |
| Deterministic natural-language intent router (no LLM needed) | ✅ working |
| Layer manager (visibility, opacity, order, style, remove, zoom-to, inspect) | ✅ working |
| Multiple overlays / layering arbitrary dataset types together | ✅ working |
| Guided tools: hillshade, slope, aspect, buffer, clip, reproject, raster statistics, raster calculator, heatmap, measure distance/area | ✅ working |
| Derived outputs registered as first-class datasets + layers | ✅ working |
| Hugging Face dataset catalog (`NoraResearchLab` org), including datasets published after this ships | ✅ working, live-verified against the Hub API |
| Dataset Library with cards, search, tag filters | ✅ working |
| Map workspaces (save/share view + layer set) | ✅ working (ephemeral -- see limitations) |
| Export: PNG (title/legend/scale/north arrow/attribution), GeoJSON, GeoTIFF, share link | ✅ working |
| Iframe embedding with query-string config + read-only mode | ✅ working |
| FastAPI + Pydantic API with human-readable errors (no tracebacks) | ✅ working |
| NetCDF / Zarr | ❌ not enabled -- clear message shown, architecture reserved |
| Reprojection, interpolation | Reprojection ✅; interpolation intentionally out of scope for v1 |

---

## Project tree

```
nora-map-engine/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, error handlers, serves built frontend
│   │   ├── config.py                # All settings, env-var driven
│   │   ├── api/                     # One router per resource
│   │   │   ├── health.py
│   │   │   ├── datasets.py          # upload / url / catalog / preview / thumbnail
│   │   │   ├── layers.py
│   │   │   ├── process.py           # hillshade / slope / aspect / buffer / clip / reproject / raster-calculator
│   │   │   ├── maps.py              # workspaces
│   │   │   ├── export.py
│   │   │   └── intent.py            # natural-language router endpoint
│   │   ├── schemas/                 # Pydantic models (dataset, layer, process, map)
│   │   ├── services/
│   │   │   ├── inspection.py        # dispatches to geospatial/ loaders, builds metadata
│   │   │   ├── visualization.py     # metadata -> recommended style + legend
│   │   │   ├── intent_router.py     # deterministic NL -> workflow
│   │   │   ├── registry.py          # in-memory dataset/layer/workspace store
│   │   │   └── bootstrap.py         # generates + registers the demo workspace on startup
│   │   ├── geospatial/
│   │   │   ├── vector.py            # GeoJSON/CSV/GeoPackage/Shapefile/GeoParquet loading + metadata
│   │   │   └── raster.py            # GeoTIFF/COG loading, stats, quicklook PNG
│   │   ├── processing/
│   │   │   ├── terrain.py           # hillshade / slope / aspect (numpy)
│   │   │   ├── vector_ops.py        # buffer / clip / reproject (geopandas)
│   │   │   └── raster_calc.py       # safe (ast-whitelisted) raster expression evaluator
│   │   ├── storage/
│   │   │   ├── base.py              # StorageBackend interface
│   │   │   ├── local.py             # ephemeral local-disk implementation
│   │   │   ├── url.py               # fetch datasets registered by public URL
│   │   │   ├── dataset_files.py     # consistent on-disk naming for dataset bytes
│   │   │   └── huggingface_catalog.py  # dynamic NoraResearchLab HF dataset catalog
│   │   ├── demo/generate_demo_data.py  # synthetic Gold Exploration Demo dataset generator
│   │   └── utils/errors.py          # every user-facing error, human-readable
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── map/                     # MapLibre integration + style-expression builders
│   │   ├── layers/LayerManager.tsx
│   │   ├── datasets/                # Dataset Library + Upload
│   │   ├── tools/ToolsPanel.tsx
│   │   ├── pages/                   # Home (onboarding) + Export
│   │   ├── components/              # Sidebar, TopBar, IntentBar, PanelDrawer, Toast
│   │   ├── workspace/WorkspaceContext.tsx  # all app state
│   │   ├── services/api.ts          # typed fetch wrapper for every endpoint
│   │   └── types/index.ts
│   └── package.json
├── tests/backend/                   # pytest: API smoke tests + processing unit tests
├── docs/
│   ├── ADDING_PERSISTENCE.md
│   ├── ADDING_DATASET_TYPES.md
│   └── AGDFS_INTEGRATION.md
├── Dockerfile                        # multi-stage: builds frontend, then serves via FastAPI
├── docker-compose.yml
├── render.yaml
├── .env.example
└── README.md
```

---

## How the pieces fit together

**One Render service, not two.** The Dockerfile builds the React frontend
first, then copies the built `dist/` next to the FastAPI backend.
`app/main.py` mounts that `dist/` and serves it for every route that isn't
`/api/*`. That means one URL to deploy, one URL to embed, and no
cross-origin configuration to get right in production. Locally, Vite's dev
server proxies `/api` to a separately-running backend instead (see below),
so you still get hot reload while developing.

**The workflow, end to end:**
1. A file (or URL, or Hugging Face catalog pick) hits `POST /api/datasets`.
2. `services/inspection.py` figures out if it's vector or raster and calls
   the matching loader in `geospatial/`, which returns real metadata:
   geometry type, CRS, bbox, feature count / raster dimensions, per-field
   min/max or distinct values.
3. `services/visualization.py` turns that metadata into a concrete style
   (which MapLibre paint properties, which color ramp, cluster vs.
   proportional-circle vs. plain points, etc.) plus a legend.
4. The frontend's `styleBuilders.ts` turns that plain-data style into real
   MapLibre expressions and adds it to the map.
5. Any processing tool (hillshade, buffer, ...) reads a dataset's bytes,
   computes a result, and registers that result the exact same way step 1
   would -- so a derived layer is a first-class dataset, not a special case.

---

## Local setup

You'll need Python 3.11+ and Node 20+.

```bash
git clone <your-fork-url> nora-map-engine
cd nora-map-engine

# --- Backend ---
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env            # optional -- defaults work out of the box
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
# --- Frontend (hot reload, proxies /api to :8000) ---
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** -- you should see the "Gold Exploration
Demo" workspace already loaded (synthetic data generated on first
backend startup, so there's something to explore with zero setup).

**Run the tests:**
```bash
cd nora-map-engine
pip install pytest  # if not already installed
python -m pytest tests/backend -v
```

**Test the production build locally** (single service, exactly like Render):
```bash
docker compose up --build
# open http://localhost:8000
```

---

## Deploying to Render

1. Push this repo to GitHub.
2. In the Render dashboard: **New +** → **Blueprint**, point it at your repo.
   Render will read `render.yaml` and provision a single free web service
   (`nora-map-engine`) using the Dockerfile automatically.
3. First deploy takes a few minutes (Node build + Python dependency
   install, all in the Docker build step). Render then boots the container
   and hits `/api/health` until it's ready.
4. Your app is live at `https://nora-map-engine.onrender.com` (or whatever
   name you gave it) -- API and UI both served from that one URL.
5. **Before going further than a demo:** open the service's Environment
   tab and set `CORS_ORIGINS` to the actual domain(s) that will embed this
   (the default `*` is fine for testing, not for production).

No Blueprint? You can also create the web service manually: **New +** →
**Web Service**, connect the repo, choose **Docker** as the environment,
leave the Dockerfile path as `./Dockerfile`, plan **Free**, health check
path `/api/health`.

**A note on the free tier specifically:** a free instance spins down after
15 minutes of inactivity and cold-starts on the next request (10-30s, since
it has to re-run dataset inspection on demo data and reconnect to Hugging
Face). It also has 512MB of RAM and an ephemeral filesystem -- both of
which shaped real decisions in this codebase (see
[Known limitations](#known-limitations)).

---

## Environment variables

All defined with defaults in `backend/app/config.py`; see `.env.example`
for the full list with explanations. The ones you're most likely to
actually change:

| Variable | Default | Purpose |
|---|---|---|
| `CORS_ORIGINS` | `*` | Comma-separated list of origins allowed to embed/call this service. Pin this before going live. |
| `HF_ORG` | `NoraResearchLab` | Which Hugging Face org's datasets populate the Dataset Library |
| `MAX_UPLOAD_MB` | `25` | Upload size cap (protects the 512MB free-tier instance) |
| `AGDFS_BASE_URL` | `https://agdfs.onrender.com` | Reserved for the AGDFS integration -- see below |
| `HF_TOKEN` | unset | Only needed if the HF org/datasets become private |

---

## Example API requests

```bash
# Health check
curl https://nora-map-engine.onrender.com/api/health

# List everything currently on the map (demo data included)
curl https://nora-map-engine.onrender.com/api/datasets

# Browse the live NORA Research Lab Hugging Face catalog
curl https://nora-map-engine.onrender.com/api/datasets/catalog

# Add a dataset from that catalog to the map
curl -X POST https://nora-map-engine.onrender.com/api/datasets/catalog/add \
  -H "Content-Type: application/json" \
  -d '{"kind":"huggingface","repo_id":"NoraResearchLab/wgm2012-world-gravity-map","filename":"gravity.parquet"}'

# Upload a file directly
curl -X POST https://nora-map-engine.onrender.com/api/datasets \
  -F "file=@occurrences.geojson"

# Ask in plain language
curl -X POST https://nora-map-engine.onrender.com/api/intent \
  -H "Content-Type: application/json" \
  -d '{"text": "compare geology and magnetic data"}'

# Generate a hillshade from a registered DEM
curl -X POST https://nora-map-engine.onrender.com/api/process/hillshade \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "demo_dem", "azimuth": 315, "altitude": 45}'
```

Full interactive docs (generated by FastAPI) are always at `/docs`.

---

## Embedding in another site

```html
<iframe
  src="https://nora-map-engine.onrender.com/?center=8.6753,9.0820&zoom=6&theme=dark&readonly=false"
  width="100%"
  height="600"
  style="border:0;"
  allow="clipboard-write"
></iframe>
```

Supported query-string config (parsed in `frontend/src/workspace/WorkspaceContext.tsx::parseEmbedConfig`):

| Param | Example | Effect |
|---|---|---|
| `center` | `8.6753,9.0820` | Initial map center (lon,lat) |
| `zoom` | `6` | Initial zoom |
| `workspace` | `map_ab12cd34` | Load a previously saved/shared workspace's view |
| `datasets` | `ds_a,ds_b` | Reserved for pre-selecting datasets on load |
| `theme` | `dark` | Reserved for a light theme variant |
| `readonly` | `true` | Hides all editing chrome (sidebar, drawers, nav controls) -- pan/zoom only |
| `tools` | `hillshade,buffer` | Reserved for restricting which tools a parent site exposes |

**Parent → embedded `postMessage` (architecture reserved, not yet wired up):**
the shape described in the original spec --
`{"type": "ADD_LAYER", "dataset": "magnetic"}` -- maps cleanly onto the
existing `addDatasetToMap()` function in `WorkspaceContext.tsx`; adding a
`window.addEventListener("message", ...)` there that calls it is a small,
isolated follow-up once a real parent integration needs it.

---

## Extending the system

See `docs/ADDING_DATASET_TYPES.md` for the exact steps (with file names) to:
- support a new file format
- add a new guided processing tool
- add a new visualization preset

See `docs/ADDING_PERSISTENCE.md` for swapping the in-memory registry for
real Postgres/Supabase persistence.

---

## Connecting to AGDFS

See `docs/AGDFS_INTEGRATION.md`. Short version: AGDFS fetches raw geodata
(imagery, DEM, magnetic/gravity, environmental layers) for a region; NORA
Map Engine inspects, styles, layers, and processes geodata once it has it.
The config already has a slot for it (`AGDFS_BASE_URL`); the integration
itself is a new storage source module following the same pattern as
`storage/huggingface_catalog.py`.

## Connecting AI/ML models

Two intentionally separate hooks:

1. **The intent router is swappable.** `services/intent_router.py` exposes
   one function, `parse_intent(text) -> IntentResult`. It's deterministic
   today; replacing its body with a call to an LLM (or a small classifier
   trained on real usage logs) doesn't require touching `api/intent.py` or
   the frontend at all -- they only know about `IntentResult`'s shape.
2. **Prospectivity / prediction outputs are just rasters.** Anything a
   model produces -- a mineral prospectivity grid, an anomaly map, a
   classification raster -- becomes a normal dataset the moment it's
   GeoTIFF/GeoParquet and goes through `POST /api/datasets`. NORA Research
   Lab's own prospectivity datasets (e.g. `Ilesha-Gold-Prospectivity-AME`
   on Hugging Face) already work this way today via the catalog
   integration -- no special-casing needed for "model output" as a
   category.

---

## Known limitations

Written down on purpose, per the brief: don't pretend a foundation is more
than it is.

- **State is ephemeral.** Datasets, layers, and workspaces live in process
  memory (workspaces are also mirrored to local JSON). A Render free-tier
  spin-down or any redeploy loses everything except the auto-regenerated
  demo workspace. Fix: `docs/ADDING_PERSISTENCE.md`.
- **Rasters render via a georeferenced image, not tiles.** `MapView.tsx`
  places raster/hillshade layers using MapLibre's `image` source (the
  dataset's PNG quicklook, positioned by its bbox corners). This is simple,
  dependency-free, and fine for demo-to-moderate raster sizes -- it is
  **not** a tiled pyramid, so a genuinely large raster will be slow to
  render and low-resolution at high zoom. Production-scale raster serving
  needs a real COG tile server (e.g. `titiler`) in front of it.
- **NetCDF and Zarr are not enabled**, even though the storage/config
  layer has slots reserved for them (`UNSUPPORTED_BUT_PLANNED` in
  `services/inspection.py`) -- uploading one returns a clear message
  rather than a fake success.
- **Terrain tools cap input size** (`terrain.MAX_TERRAIN_PX = 2000px`
  per side) to stay safely inside 512MB of RAM. Larger DEMs need
  downsampling first, or a bigger instance.
- **The raster calculator requires both inputs on the same grid** (same
  dimensions/transform) -- no resampling step yet.
- **Single-tenant.** There's one shared dataset/layer registry per running
  instance, not per-user workspaces. Fine for an internal tool or a single
  embedded context; a multi-tenant deployment needs the registry keyed by
  user/session in addition to real persistence.
- **The frontend bundle is ~1MB** (MapLibre + Turf are both sizeable).
  Fine for a map application, but if that matters for your embed context,
  code-splitting Turf into a dynamic import (only the Tools panel's
  measure feature needs it) is a quick win.
