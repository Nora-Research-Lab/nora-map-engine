import React, { useRef, useState } from "react";
import { useWorkspace } from "../workspace/WorkspaceContext";
import * as api from "../services/api";

export const DatasetUpload: React.FC = () => {
  const { refreshDatasets, addDatasetToMap, notify } = useWorkspace();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [urlValue, setUrlValue] = useState("");

  const handleFile = async (file: File) => {
    setBusy(true);
    try {
      const { dataset, warnings } = await api.uploadDataset(file);
      await refreshDatasets();
      warnings.forEach((w) => notify(w));
      notify(`"${dataset.name}" is ready. Add it to the map below.`);
      await addDatasetToMap(dataset.id);
    } catch (e: any) {
      notify(e.hint ? `${e.message} ${e.hint}` : e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleUrl = async () => {
    if (!urlValue.trim()) return;
    setBusy(true);
    try {
      const { dataset } = await api.registerFromUrl(urlValue.trim());
      await refreshDatasets();
      await addDatasetToMap(dataset.id);
      setUrlValue("");
    } catch (e: any) {
      notify(e.hint ? `${e.message} ${e.hint}` : e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div
        className={`dropzone ${dragActive ? "active" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          hidden
          accept=".geojson,.json,.csv,.gpkg,.zip,.parquet,.geoparquet,.tif,.tiff"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        <div className="label">Add a dataset</div>
        <p style={{ margin: "6px 0", fontSize: 13, color: "var(--ink-dim)" }}>
          {busy ? "Reading your file…" : "Drop a file here, or click to browse"}
        </p>
        <p style={{ margin: 0, fontSize: 11, color: "var(--ink-faint)" }}>
          GeoJSON, CSV (lat/lon), GeoPackage, Shapefile (.zip), GeoParquet, or GeoTIFF
        </p>
      </div>
      <div className="divider" />
      <div style={{ display: "flex", gap: 6 }}>
        <input
          placeholder="…or paste a public dataset URL"
          value={urlValue}
          onChange={(e) => setUrlValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleUrl()}
          style={{ flex: 1 }}
        />
        <button className="btn btn-sm" disabled={busy} onClick={handleUrl}>Add</button>
      </div>
    </div>
  );
};
