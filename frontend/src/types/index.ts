export type DatasetKind = "vector" | "raster";
export type DatasetOrigin = "upload" | "url" | "huggingface" | "demo" | "derived";
export type FieldType = "numeric" | "categorical" | "text" | "date";

export interface FieldInfo {
  name: string;
  type: FieldType;
  min?: number | null;
  max?: number | null;
  unit?: string | null;
  distinct_values?: string[] | null;
  missing_count: number;
}

export interface DatasetMetadata {
  id: string;
  name: string;
  description?: string | null;
  kind: DatasetKind;
  origin: DatasetOrigin;
  format: string;
  geometry_type?: string | null;
  crs?: string | null;
  crs_confident: boolean;
  bbox?: [number, number, number, number] | null;
  feature_count?: number | null;
  width?: number | null;
  height?: number | null;
  band_count?: number | null;
  resolution?: number | null;
  nodata?: number | null;
  fields: FieldInfo[];
  size_bytes?: number | null;
  tags: string[];
  source_ref: Record<string, unknown>;
  recommended_preset?: string | null;
  created_at: string;
  style?: Record<string, unknown> | null;
}

export interface DatasetSummary {
  id: string;
  name: string;
  kind: DatasetKind;
  format: string;
  origin: DatasetOrigin;
  coverage?: string | null;
  feature_count?: number | null;
  band_count?: number | null;
  resolution?: number | null;
  tags: string[];
  thumbnail_note?: string | null;
  materialized: boolean;
}

export interface DatasetPreview {
  dataset_id: string;
  kind: DatasetKind;
  geojson?: GeoJSON.FeatureCollection | null;
  truncated: boolean;
  raster_preview_url?: string | null;
  stats?: Record<string, unknown> | null;
}

export type LayerRenderType =
  | "circle"
  | "proportional_circle"
  | "cluster"
  | "line"
  | "fill"
  | "choropleth"
  | "heatmap"
  | "raster"
  | "hillshade";

export interface LegendEntry {
  value: string;
  color: string;
}

export interface Legend {
  type: "single" | "categorical" | "gradient";
  color?: string;
  field?: string | null;
  entries?: LegendEntry[];
  ramp?: string[];
  min?: number | null;
  max?: number | null;
}

export interface Layer {
  id: string;
  dataset_id: string;
  name: string;
  render_type: LayerRenderType;
  visible: boolean;
  opacity: number;
  order: number;
  style: Record<string, any>;
  legend?: Legend | null;
  bbox?: [number, number, number, number] | null;
  created_at: string;
}

export interface MapView {
  center: [number, number];
  zoom: number;
  bearing: number;
  pitch: number;
}

export interface MapWorkspace {
  id: string;
  name: string;
  description?: string | null;
  view: MapView;
  layer_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface ProcessResult {
  dataset_id: string;
  layer_suggested: boolean;
  message: string;
}

export interface IntentResponse {
  actions: string[];
  domains: string[];
  panel: "home" | "datasets" | "layers" | "tools" | "export";
  tool?: string | null;
  hint: string;
  matched_datasets: { id: string; name: string; tags: string[] }[];
}

export type PanelId = "home" | "datasets" | "layers" | "tools" | "export" | null;

export interface EmbedConfig {
  center?: [number, number];
  zoom?: number;
  workspaceId?: string;
  datasetIds: string[];
  theme: string;
  readOnly: boolean;
  enabledTools?: string[];
}
