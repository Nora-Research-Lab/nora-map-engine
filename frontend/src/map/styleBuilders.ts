/**
 * Translates the backend's plain-data layer style (from
 * app.services.visualization on the backend) into real MapLibre GL
 * paint/layout expressions. Kept separate from MapView so the mapping
 * logic for each render_type is easy to find and extend.
 */
import type { Layer } from "../types";

const FALLBACK_COLOR = "#c97c4a";

/** Builds a MapLibre `match` expression from the legend entries the backend
 * already computed (value -> color), so the frontend never has to guess
 * which distinct values exist -- it just renders what was inspected. */
function categoricalExpression(field: string, layer: Layer): any {
  const entries = layer.legend?.entries ?? [];
  if (!entries.length) return layer.style?.fill_color ?? layer.style?.color ?? FALLBACK_COLOR;
  const pairs: any[] = [];
  entries.forEach((e) => pairs.push(e.value, e.color));
  return ["match", ["to-string", ["get", field]], ...pairs, entries[0].color];
}

export function circlePaint(layer: Layer): Record<string, any> {
  const style = layer.style || {};
  const radius = style.size_field
    ? (["interpolate", ["linear"], ["coalesce", ["get", style.size_field], 0], 0, 3, 100, 16] as any)
    : style.radius ?? 5;

  const color = style.color_field ? categoricalExpression(style.color_field, layer) : style.color ?? FALLBACK_COLOR;

  return {
    "circle-radius": radius,
    "circle-color": color,
    "circle-opacity": layer.opacity,
    "circle-stroke-width": 1,
    "circle-stroke-color": "#0c1310",
  };
}

export function clusterPaint(): Record<string, any> {
  return {
    "circle-color": ["step", ["get", "point_count"], "#4fb6b0", 25, "#d9a441", 100, "#c97c4a"],
    "circle-radius": ["step", ["get", "point_count"], 14, 25, 18, 100, 24],
    "circle-stroke-width": 1,
    "circle-stroke-color": "#0c1310",
  };
}

export function linePaint(layer: Layer): Record<string, any> {
  const style = layer.style || {};
  const width = style.width_field
    ? (["interpolate", ["linear"], ["coalesce", ["get", style.width_field], 0], 0, 1, 100, 6] as any)
    : style.width ?? 2;
  return {
    "line-color": style.color ?? FALLBACK_COLOR,
    "line-width": width,
    "line-opacity": layer.opacity,
  };
}

export function fillPaint(layer: Layer): Record<string, any> {
  const style = layer.style || {};
  const color = style.color_field ? categoricalExpression(style.color_field, layer) : style.fill_color ?? FALLBACK_COLOR;
  return {
    "fill-color": color,
    "fill-opacity": (style.fill_opacity ?? 0.55) * layer.opacity,
    "fill-outline-color": style.outline_color ?? "#0c1310",
  };
}

export function choroplethPaint(layer: Layer): Record<string, any> {
  const style = layer.style || {};
  const legend = layer.legend;
  const min = legend?.min ?? 0;
  const max = legend?.max ?? 1;
  const ramp: string[] = style.ramp ?? ["#16324f", "#1b5e63", "#3b8c6e", "#8fbf6b", "#e8d25a", "#e8895a", "#c94a4a"];
  const stops: any[] = [];
  ramp.forEach((color, i) => {
    const t = min + ((max - min) * i) / (ramp.length - 1);
    stops.push(t, color);
  });
  return {
    "fill-color": ["interpolate", ["linear"], ["coalesce", ["get", style.field], min], ...stops] as any,
    "fill-opacity": 0.75 * layer.opacity,
    "fill-outline-color": "#0c1310",
  };
}

export function heatmapPaint(layer: Layer): Record<string, any> {
  return {
    "heatmap-weight": 0.6,
    "heatmap-intensity": 1,
    "heatmap-color": [
      "interpolate", ["linear"], ["heatmap-density"],
      0, "rgba(0,0,0,0)",
      0.2, "#316663",
      0.4, "#4fb6b0",
      0.6, "#d9a441",
      0.8, "#c97c4a",
      1, "#c9584a",
    ] as any,
    "heatmap-radius": 24,
    "heatmap-opacity": layer.opacity,
  };
}
