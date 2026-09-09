# Connecting to AGDFS

[AGDFS](https://agdfs.onrender.com) (Automated Geological Data Fetching
System) is a separate NORA Research Lab service that already provides a
unified API for satellite imagery, elevation, geophysics, and environmental
data (imagery, DEM, magnetic/gravity via WGM2012, soil, weather,
earthquakes, air quality), plus an MCP layer at `/mcp`.

NORA Map Engine and AGDFS are complementary, not overlapping: AGDFS
*fetches* raw geodata for a bounding box; NORA Map Engine *inspects,
styles, layers, and processes* geodata once it's in hand. The natural
integration is to let NORA Map Engine call AGDFS as another dataset source,
the same way it already calls Hugging Face.

## Suggested approach

1. Add an `AGDFSStorage`/`agdfs_client.py` module next to
   `app/storage/huggingface_catalog.py`, using `settings.agdfs_base_url`
   (already wired into `app/config.py`).
2. Expose AGDFS's endpoints (`/imagery`, `/dem`, `/geophysics/magnetic`,
   `/geophysics/gravity`, `/environment/*`) as another Dataset Library
   section -- "Fetch from AGDFS" alongside "Hugging Face Catalog" -- with a
   simple bbox + layer-type form instead of a file picker, since AGDFS
   returns data for a region rather than a fixed file.
3. Register the response the same way `datasets.py` already registers a
   Hugging Face or uploaded file: run it through `app/services/inspection.py`,
   store the bytes via `app/storage/dataset_files.py`, and hand back a
   normal `DatasetMetadata` -- from that point on it's a first-class dataset
   like any other, and every layer/tool/export feature in the product
   already works with it.
4. Longer term, since AGDFS already exposes an MCP server, an AI assistant
   could drive both services together: ask AGDFS for data, then ask NORA
   Map Engine to visualize it -- without either service needing to know
   about the other's internals.
