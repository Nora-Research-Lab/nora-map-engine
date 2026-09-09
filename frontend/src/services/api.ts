import type {
  DatasetMetadata,
  DatasetPreview,
  DatasetSummary,
  IntentResponse,
  Layer,
  MapWorkspace,
  ProcessResult,
} from "../types";

const BASE = "/api";

export class ApiError extends Error {
  hint?: string;
  status: number;
  constructor(message: string, status: number, hint?: string) {
    super(message);
    this.status = status;
    this.hint = hint;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    let hint: string | undefined;
    try {
      const body = await res.json();
      message = body.error || message;
      hint = body.hint;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(message, res.status, hint);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// --- Health ---
export const getHealth = () => request<{ status: string }>("/health");

// --- Datasets ---
export const listDatasets = (includeCatalog = false) =>
  request<DatasetSummary[]>(`/datasets?include_catalog=${includeCatalog}`);

export const listCatalog = (refresh = false) =>
  request<DatasetSummary[]>(`/datasets/catalog?refresh=${refresh}`);

export const listCatalogFiles = (repoId: string) =>
  request<{ repo_id: string; files: string[] }>(`/datasets/catalog/${encodeURIComponent(repoId)}/files`);

export const getDataset = (id: string) => request<DatasetMetadata>(`/datasets/${id}`);

export const getDatasetPreview = (id: string) => request<DatasetPreview>(`/datasets/${id}/preview`);

export const uploadDataset = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return request<{ dataset: DatasetMetadata; warnings: string[] }>("/datasets", {
    method: "POST",
    body: form,
  });
};

export const registerFromUrl = (url: string, name?: string) =>
  request<{ dataset: DatasetMetadata; warnings: string[] }>("/datasets/url", {
    method: "POST",
    body: JSON.stringify({ kind: "url", url, name }),
  });

export const addFromCatalog = (repoId: string, filename: string, name?: string) =>
  request<{ dataset: DatasetMetadata; warnings: string[] }>("/datasets/catalog/add", {
    method: "POST",
    body: JSON.stringify({ kind: "huggingface", repo_id: repoId, filename, name }),
  });

export const deleteDataset = (id: string) => request(`/datasets/${id}`, { method: "DELETE" });

// --- Layers ---
export const listLayers = () => request<Layer[]>("/layers");

export const createLayer = (datasetId: string, name?: string) =>
  request<Layer>("/layers", { method: "POST", body: JSON.stringify({ dataset_id: datasetId, name }) });

export const updateLayer = (id: string, patch: Partial<Layer> & { style_overrides?: Record<string, any> }) =>
  request<Layer>(`/layers/${id}`, { method: "PATCH", body: JSON.stringify(patch) });

export const deleteLayer = (id: string) => request(`/layers/${id}`, { method: "DELETE" });

// --- Maps / workspaces ---
export const listMaps = () => request<MapWorkspace[]>("/maps");
export const getMap = (id: string) => request<MapWorkspace>(`/maps/${id}`);
export const createMap = (payload: Partial<MapWorkspace> & { name: string }) =>
  request<MapWorkspace>("/maps", { method: "POST", body: JSON.stringify(payload) });
export const updateMap = (id: string, payload: Partial<MapWorkspace> & { name: string }) =>
  request<MapWorkspace>(`/maps/${id}`, { method: "PUT", body: JSON.stringify(payload) });

// --- Processing ---
export const processHillshade = (datasetId: string, azimuth = 315, altitude = 45) =>
  request<ProcessResult>("/process/hillshade", {
    method: "POST",
    body: JSON.stringify({ dataset_id: datasetId, azimuth, altitude }),
  });

export const processSlope = (datasetId: string, units: "degrees" | "percent" = "degrees") =>
  request<ProcessResult>("/process/slope", { method: "POST", body: JSON.stringify({ dataset_id: datasetId, units }) });

export const processAspect = (datasetId: string) =>
  request<ProcessResult>("/process/aspect", { method: "POST", body: JSON.stringify({ dataset_id: datasetId }) });

export const processBuffer = (datasetId: string, distanceM: number) =>
  request<ProcessResult>("/process/buffer", {
    method: "POST",
    body: JSON.stringify({ dataset_id: datasetId, distance_m: distanceM }),
  });

export const processClip = (datasetId: string, maskDatasetId: string) =>
  request<ProcessResult>("/process/clip", {
    method: "POST",
    body: JSON.stringify({ dataset_id: datasetId, mask_dataset_id: maskDatasetId }),
  });

export const processReproject = (datasetId: string, targetCrs: string) =>
  request<ProcessResult>("/process/reproject", {
    method: "POST",
    body: JSON.stringify({ dataset_id: datasetId, target_crs: targetCrs }),
  });

export const processRasterCalculator = (datasetAId: string, datasetBId: string | null, expression: string) =>
  request<ProcessResult>("/process/raster-calculator", {
    method: "POST",
    body: JSON.stringify({ dataset_a_id: datasetAId, dataset_b_id: datasetBId, expression }),
  });

// --- Intent ---
export const interpretIntent = (text: string) =>
  request<IntentResponse>("/intent", { method: "POST", body: JSON.stringify({ text }) });

// --- Export ---
export const getExportConfig = (mapId: string) => request<any>(`/export/config/${mapId}`);
export const geojsonDownloadUrl = (datasetId: string) => `${BASE}/export/dataset/${datasetId}.geojson`;
export const geotiffDownloadUrl = (datasetId: string) => `${BASE}/export/dataset/${datasetId}.tif`;
export const thumbnailUrl = (datasetId: string) => `${BASE}/datasets/${datasetId}/thumbnail.png`;
