import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { DatasetSummary, EmbedConfig, Layer, MapWorkspace, PanelId } from "../types";
import * as api from "../services/api";
import type maplibregl from "maplibre-gl";

export type MeasureMode = "distance" | "area" | null;

interface WorkspaceState {
  datasets: DatasetSummary[];
  layers: Layer[];
  workspaces: MapWorkspace[];
  activePanel: PanelId;
  loading: boolean;
  error: string | null;
  embed: EmbedConfig;
  flyToTarget: [number, number, number, number] | null; // bbox to zoom to
  refreshDatasets: () => Promise<void>;
  refreshLayers: () => Promise<void>;
  addDatasetToMap: (datasetId: string) => Promise<void>;
  removeLayer: (layerId: string) => Promise<void>;
  patchLayer: (layerId: string, patch: Partial<Layer> & { style_overrides?: Record<string, any> }) => Promise<void>;
  setActivePanel: (panel: PanelId) => void;
  zoomToLayer: (layer: Layer) => void;
  setError: (msg: string | null) => void;
  notify: (msg: string) => void;
  toast: string | null;
  measureMode: MeasureMode;
  setMeasureMode: (mode: MeasureMode) => void;
  mapRef: React.MutableRefObject<maplibregl.Map | null>;
}

const WorkspaceContext = createContext<WorkspaceState | null>(null);

function parseEmbedConfig(): EmbedConfig {
  const params = new URLSearchParams(window.location.search);
  const centerParam = params.get("center");
  const center = centerParam
    ? (centerParam.split(",").map(Number) as [number, number])
    : undefined;
  return {
    center,
    zoom: params.get("zoom") ? Number(params.get("zoom")) : undefined,
    workspaceId: params.get("workspace") ?? undefined,
    datasetIds: params.get("datasets")?.split(",").filter(Boolean) ?? [],
    theme: params.get("theme") ?? "dark",
    readOnly: params.get("readonly") === "true",
    enabledTools: params.get("tools")?.split(",").filter(Boolean),
  };
}

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [layers, setLayers] = useState<Layer[]>([]);
  const [workspaces, setWorkspaces] = useState<MapWorkspace[]>([]);
  const [activePanel, setActivePanel] = useState<PanelId>("home");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [flyToTarget, setFlyToTarget] = useState<[number, number, number, number] | null>(null);
  const [measureMode, setMeasureMode] = useState<MeasureMode>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const embed = useMemo(() => parseEmbedConfig(), []);

  const notify = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 3500);
  }, []);

  const refreshDatasets = useCallback(async () => {
    try {
      const items = await api.listDatasets(true);
      setDatasets(items);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  const refreshLayers = useCallback(async () => {
    try {
      const items = await api.listLayers();
      setLayers(items.sort((a, b) => a.order - b.order));
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([refreshDatasets(), refreshLayers(), api.listMaps().then(setWorkspaces)])
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [refreshDatasets, refreshLayers]);

  const addDatasetToMap = useCallback(
    async (datasetId: string) => {
      try {
        let realId = datasetId;
        if (datasetId.startsWith("hf:")) {
          const repoId = datasetId.slice(3);
          const { files } = await api.listCatalogFiles(repoId);
          const file = files[0];
          if (!file) {
            notify("That dataset doesn't have a readable data file yet.");
            return;
          }
          const { dataset } = await api.addFromCatalog(repoId, file);
          realId = dataset.id;
          await refreshDatasets();
        }
        const layer = await api.createLayer(realId);
        setLayers((prev) => [...prev, layer].sort((a, b) => a.order - b.order));
        notify(`Added "${layer.name}" to the map.`);
        setActivePanel("layers");
      } catch (e: any) {
        notify(e.hint ? `${e.message} ${e.hint}` : e.message);
      }
    },
    [notify, refreshDatasets]
  );

  const removeLayer = useCallback(async (layerId: string) => {
    await api.deleteLayer(layerId);
    setLayers((prev) => prev.filter((l) => l.id !== layerId));
  }, []);

  const patchLayer = useCallback(
    async (layerId: string, patch: Partial<Layer> & { style_overrides?: Record<string, any> }) => {
      const updated = await api.updateLayer(layerId, patch);
      setLayers((prev) => prev.map((l) => (l.id === layerId ? updated : l)));
    },
    []
  );

  const zoomToLayer = useCallback((layer: Layer) => {
    if (layer.bbox) setFlyToTarget([...layer.bbox] as [number, number, number, number]);
  }, []);

  const value: WorkspaceState = {
    datasets,
    layers,
    workspaces,
    activePanel,
    loading,
    error,
    embed,
    flyToTarget,
    refreshDatasets,
    refreshLayers,
    addDatasetToMap,
    removeLayer,
    patchLayer,
    setActivePanel,
    zoomToLayer,
    setError,
    notify,
    toast,
    measureMode,
    setMeasureMode,
    mapRef,
  };

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
};

export function useWorkspace(): WorkspaceState {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return ctx;
}
