# Adding a new dataset format, processing tool, or visualization preset

## A new dataset format
1. Add a loader function to `app/geospatial/vector.py` (vector) or
   `app/geospatial/raster.py` (raster) that takes raw bytes and returns a
   GeoDataFrame (vector) or extracts the fields `extract_raster_metadata`
   needs (raster).
2. Register the file extension in `VECTOR_EXTENSIONS`/`RASTER_EXTENSIONS`
   in that same file.
3. Wire it into `app/services/inspection.py::guess_kind` if it needs
   special-casing beyond the extension check.

## A new processing tool
1. Write the actual computation as a pure function in
   `app/processing/<area>.py` (see `terrain.py` for the pattern: read
   bytes in, return `(result_bytes, stats)` out). Keep it dependency-light
   and bound its memory/pixel usage the way `terrain.MAX_TERRAIN_PX` does.
2. Add a request schema to `app/schemas/process.py`.
3. Add an endpoint to `app/api/process.py` that loads the source dataset(s),
   calls your function, and registers the result via `_register_derived_raster`
   or `_register_derived_vector` (this is what makes the output a
   first-class dataset + layer automatically).
4. Add the corresponding form to `frontend/src/tools/ToolsPanel.tsx` and a
   client function to `frontend/src/services/api.ts`.

## A new visualization preset
1. Add the logic to `app/services/visualization.py` -- either extend
   `recommend_vector_style`/`recommend_raster_style`, or add a new
   `render_type` to `app/schemas/layer.py::LayerRenderType`.
2. Teach the frontend how to draw it: add a paint-builder function to
   `frontend/src/map/styleBuilders.ts` and a branch in
   `frontend/src/map/MapView.tsx::addLayerToMap`.
