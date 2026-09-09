import React, { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import * as turf from "@turf/turf";
import { useWorkspace } from "../workspace/WorkspaceContext";
import * as api from "../services/api";
import type { Layer } from "../types";
import { choroplethPaint, circlePaint, clusterPaint, fillPaint, heatmapPaint, linePaint } from "./styleBuilders";

// A plain OSM raster basemap -- no API key required, works out of the box
// on a fresh clone or a fresh Render deploy.
const BASEMAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  glyphs: "https://fonts.openmaptiles.org/{fontstack}/{range}.pbf",
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "&copy; OpenStreetMap contributors",
      maxzoom: 19,
    },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#0c1310" } },
    { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.9, "raster-saturation": -0.3 } },
  ],
};

const MANAGED_PREFIX = "nora-";

export const MapView: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { layers, embed, flyToTarget, mapRef, measureMode, setMeasureMode, notify } = useWorkspace();
  const previewCache = useRef<Map<string, GeoJSON.FeatureCollection>>(new Map());
  const [cursorPos, setCursorPos] = useState<{ lng: number; lat: number } | null>(null);
  const measurePoints = useRef<[number, number][]>([]);
  const [, forceTick] = useState(0);

  // --- Initialize the map once ---
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    let cancelled = false;

    const init = async () => {
      let center = embed.center ?? [8.6753, 9.082];
      let zoom = embed.zoom ?? 5.5;
      let bearing = 0;
      let pitch = 0;

      if (embed.workspaceId) {
        try {
          const workspace = await api.getMap(embed.workspaceId);
          center = workspace.view.center;
          zoom = workspace.view.zoom;
          bearing = workspace.view.bearing;
          pitch = workspace.view.pitch;
        } catch {
          // Fall back to defaults silently -- the workspace may have been
          // lost to an instance restart (see storage/base.py notes).
        }
      }

      if (cancelled || !containerRef.current) return;

      const map = new maplibregl.Map({
        container: containerRef.current,
        style: BASEMAP_STYLE,
        center,
        zoom,
        bearing,
        pitch,
        attributionControl: { compact: true },
      });
      if (!embed.readOnly) {
        map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
      }
      map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
      map.on("mousemove", (e) => setCursorPos({ lng: e.lngLat.lng, lat: e.lngLat.lat }));
      if (embed.readOnly) {
        map.scrollZoom.disable();
        map.boxZoom.disable();
        map.dragRotate.disable();
        map.dragPan.enable();
      }
      mapRef.current = map;
      forceTick((t) => t + 1);
    };

    init();

    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Fly to a requested bbox (zoom-to-layer) ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !flyToTarget) return;
    const [minx, miny, maxx, maxy] = flyToTarget;
    map.fitBounds([[minx, miny], [maxx, maxy]], { padding: 60, duration: 800, maxZoom: 15 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flyToTarget]);

  // --- Sync layers state -> MapLibre sources/layers ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    let cancelled = false;

    const sync = async () => {
      if (!map.isStyleLoaded()) {
        map.once("load", sync);
        return;
      }

      // Full rebuild of managed layers on every change. Simpler and more
      // correct than incremental diffing for this MVP's scale (a handful
      // to a few dozen layers) -- a worthwhile trade for reliability.
      removeManagedLayers(map);

      for (const layer of [...layers].sort((a, b) => a.order - b.order)) {
        if (cancelled) return;
        try {
          await addLayerToMap(map, layer, previewCache.current);
        } catch (err) {
          console.error(`Failed to render layer "${layer.name}"`, err);
        }
      }
    };

    sync();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(layers.map((l) => [l.id, l.visible, l.opacity, l.order, l.render_type, l.style])), forceTick]);

  // --- Measure tool ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (!measureMode) {
      clearMeasureLayer(map);
      measurePoints.current = [];
      map.getCanvas().style.cursor = "";
      return;
    }
    map.getCanvas().style.cursor = "crosshair";

    const handleClick = (e: maplibregl.MapMouseEvent) => {
      measurePoints.current.push([e.lngLat.lng, e.lngLat.lat]);
      drawMeasureLayer(map, measurePoints.current, measureMode);
    };

    const handleDblClick = (e: maplibregl.MapMouseEvent) => {
      e.preventDefault();
      const pts = measurePoints.current;
      if (pts.length < 2) return;
      if (measureMode === "distance") {
        const line = turf.lineString(pts);
        const km = turf.length(line, { units: "kilometers" });
        notify(`Distance: ${km < 1 ? `${(km * 1000).toFixed(0)} m` : `${km.toFixed(2)} km`}`);
      } else {
        const ring = [...pts, pts[0]];
        const poly = turf.polygon([ring]);
        const sqm = turf.area(poly);
        const label = sqm > 1_000_000 ? `${(sqm / 1_000_000).toFixed(2)} km²` : `${sqm.toFixed(0)} m²`;
        notify(`Area: ${label}`);
      }
      measurePoints.current = [];
      setMeasureMode(null);
    };

    map.on("click", handleClick);
    map.on("dblclick", handleDblClick);
    return () => {
      map.off("click", handleClick);
      map.off("dblclick", handleDblClick);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [measureMode]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      {cursorPos && !embed.readOnly && (
        <div className="coord-readout mono">
          {cursorPos.lat.toFixed(4)}, {cursorPos.lng.toFixed(4)}
        </div>
      )}
      {measureMode && (
        <div className="measure-hint panel">
          {measureMode === "distance" ? "Click to add points, double-click to finish measuring distance." : "Click to add points, double-click to finish measuring area."}
          <button className="btn btn-sm btn-ghost" onClick={() => setMeasureMode(null)} style={{ marginLeft: 8 }}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
};

function removeManagedLayers(map: maplibregl.Map) {
  const style = map.getStyle();
  if (!style) return;
  for (const l of [...style.layers]) {
    if (l.id.startsWith(MANAGED_PREFIX)) {
      if (map.getLayer(l.id)) map.removeLayer(l.id);
    }
  }
  for (const sourceId of Object.keys(style.sources)) {
    if (sourceId.startsWith(MANAGED_PREFIX) && !map.getStyle().layers.some((l) => (l as any).source === sourceId)) {
      map.removeSource(sourceId);
    }
  }
}

async function getPreview(datasetId: string, cache: Map<string, GeoJSON.FeatureCollection>) {
  if (cache.has(datasetId)) return cache.get(datasetId)!;
  const preview = await api.getDatasetPreview(datasetId);
  if (preview.geojson) cache.set(datasetId, preview.geojson);
  return preview.geojson;
}

async function addLayerToMap(map: maplibregl.Map, layer: Layer, cache: Map<string, GeoJSON.FeatureCollection>) {
  const sourceId = `${MANAGED_PREFIX}src-${layer.id}`;
  const layerId = `${MANAGED_PREFIX}lyr-${layer.id}`;
  const visibility = layer.visible ? "visible" : "none";

  if (layer.render_type === "raster" || layer.render_type === "hillshade") {
    if (!layer.bbox) return;
    const [minx, miny, maxx, maxy] = layer.bbox;
    map.addSource(sourceId, {
      type: "image",
      url: api.thumbnailUrl(layer.dataset_id),
      coordinates: [
        [minx, maxy],
        [maxx, maxy],
        [maxx, miny],
        [minx, miny],
      ],
    });
    map.addLayer({
      id: layerId,
      type: "raster",
      source: sourceId,
      layout: { visibility },
      paint: { "raster-opacity": layer.opacity },
    });
    return;
  }

  const geojson = await getPreview(layer.dataset_id, cache);
  if (!geojson) return;

  if (layer.render_type === "cluster") {
    map.addSource(sourceId, { type: "geojson", data: geojson, cluster: true, clusterRadius: 50, clusterMaxZoom: 14 });
    map.addLayer({
      id: `${layerId}-clusters`,
      type: "circle",
      source: sourceId,
      filter: ["has", "point_count"],
      layout: { visibility },
      paint: clusterPaint(),
    });
    map.addLayer({
      id: `${layerId}-count`,
      type: "symbol",
      source: sourceId,
      filter: ["has", "point_count"],
      layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12, visibility },
      paint: { "text-color": "#0c1310" },
    });
    map.addLayer({
      id: layerId,
      type: "circle",
      source: sourceId,
      filter: ["!", ["has", "point_count"]],
      layout: { visibility },
      paint: circlePaint(layer),
    });
    return;
  }

  map.addSource(sourceId, { type: "geojson", data: geojson });

  if (layer.render_type === "heatmap") {
    map.addLayer({ id: layerId, type: "heatmap", source: sourceId, layout: { visibility }, paint: heatmapPaint(layer) });
  } else if (layer.render_type === "circle" || layer.render_type === "proportional_circle") {
    map.addLayer({ id: layerId, type: "circle", source: sourceId, layout: { visibility }, paint: circlePaint(layer) });
  } else if (layer.render_type === "line") {
    map.addLayer({ id: layerId, type: "line", source: sourceId, layout: { visibility }, paint: linePaint(layer) });
  } else if (layer.render_type === "choropleth") {
    map.addLayer({ id: layerId, type: "fill", source: sourceId, layout: { visibility }, paint: choroplethPaint(layer) });
    map.addLayer({
      id: `${layerId}-outline`,
      type: "line",
      source: sourceId,
      layout: { visibility },
      paint: { "line-color": "#0c1310", "line-width": 0.5 },
    });
  } else {
    map.addLayer({ id: layerId, type: "fill", source: sourceId, layout: { visibility }, paint: fillPaint(layer) });
    map.addLayer({
      id: `${layerId}-outline`,
      type: "line",
      source: sourceId,
      layout: { visibility },
      paint: { "line-color": "#0c1310", "line-width": 0.5 },
    });
  }
}

function clearMeasureLayer(map: maplibregl.Map) {
  if (map.getLayer("measure-line")) map.removeLayer("measure-line");
  if (map.getLayer("measure-fill")) map.removeLayer("measure-fill");
  if (map.getLayer("measure-points")) map.removeLayer("measure-points");
  if (map.getSource("measure")) map.removeSource("measure");
}

function drawMeasureLayer(map: maplibregl.Map, points: [number, number][], mode: "distance" | "area") {
  clearMeasureLayer(map);
  if (points.length < 1) return;
  const features: GeoJSON.Feature[] = [{ type: "Feature", properties: {}, geometry: { type: "MultiPoint", coordinates: points } }];
  if (points.length >= 2) {
    if (mode === "distance") {
      features.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: points } });
    } else {
      features.push({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[...points, points[0]]] } });
    }
  }
  map.addSource("measure", { type: "geojson", data: { type: "FeatureCollection", features } });
  if (mode === "distance") {
    map.addLayer({ id: "measure-line", type: "line", source: "measure", filter: ["==", "$type", "LineString"], paint: { "line-color": "#d9a441", "line-width": 2, "line-dasharray": [2, 1] } });
  } else {
    map.addLayer({ id: "measure-fill", type: "fill", source: "measure", filter: ["==", "$type", "Polygon"], paint: { "fill-color": "#d9a441", "fill-opacity": 0.25 } });
  }
  map.addLayer({ id: "measure-points", type: "circle", source: "measure", filter: ["==", "$type", "Point"], paint: { "circle-radius": 4, "circle-color": "#d9a441" } });
}
