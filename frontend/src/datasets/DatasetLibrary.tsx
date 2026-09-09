import React, { useMemo, useState } from "react";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { DatasetUpload } from "./DatasetUpload";
import type { DatasetSummary } from "../types";

const TAG_FILTERS = ["gold", "mineral", "geology", "faults", "geophysics", "dem", "rivers", "environment", "sediment"];

function DatasetCard({ dataset }: { dataset: DatasetSummary }) {
  const { addDatasetToMap } = useWorkspace();
  const [adding, setAdding] = useState(false);

  return (
    <div className="card dataset-card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>{dataset.name}</div>
          <div style={{ fontSize: 12, color: "var(--ink-dim)", marginTop: 2 }}>
            {dataset.kind === "raster" ? "Raster" : "Vector"} · {dataset.format.toUpperCase()}
            {dataset.origin === "huggingface" && !dataset.materialized && " · Hugging Face"}
          </div>
        </div>
        <span className="tag">{dataset.origin}</span>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, margin: "8px 0" }}>
        {dataset.tags.map((t) => (
          <span key={t} className="tag">{t}</span>
        ))}
      </div>

      <div style={{ fontSize: 12, color: "var(--ink-dim)", display: "flex", flexDirection: "column", gap: 2 }}>
        {dataset.coverage && <span>Coverage: {dataset.coverage}</span>}
        {dataset.feature_count != null && <span className="mono">{dataset.feature_count.toLocaleString()} features</span>}
        {dataset.band_count != null && <span className="mono">{dataset.band_count} band(s)</span>}
        {dataset.resolution != null && <span className="mono">{dataset.resolution.toFixed(4)}° resolution</span>}
        {dataset.thumbnail_note && <span>{dataset.thumbnail_note}</span>}
      </div>

      <button
        className="btn btn-primary btn-sm btn-block"
        style={{ marginTop: 10 }}
        disabled={adding}
        onClick={async () => {
          setAdding(true);
          await addDatasetToMap(dataset.id);
          setAdding(false);
        }}
      >
        {adding ? "Adding…" : dataset.materialized ? "Add to Map" : "Fetch & Add to Map"}
      </button>
    </div>
  );
}

export const DatasetLibrary: React.FC = () => {
  const { datasets, loading } = useWorkspace();
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    return datasets.filter((d) => {
      if (activeTag && !d.tags.includes(activeTag)) return false;
      if (query && !d.name.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    });
  }, [datasets, activeTag, query]);

  return (
    <div>
      <DatasetUpload />

      <input
        placeholder="Search datasets…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{ width: "100%", marginBottom: 8 }}
      />

      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
        {TAG_FILTERS.map((tag) => (
          <button
            key={tag}
            className="tag"
            style={{
              cursor: "pointer",
              borderColor: activeTag === tag ? "var(--copper)" : undefined,
              color: activeTag === tag ? "var(--copper)" : undefined,
            }}
            onClick={() => setActiveTag(activeTag === tag ? null : tag)}
          >
            {tag}
          </button>
        ))}
      </div>

      {loading && <p style={{ color: "var(--ink-dim)", fontSize: 13 }}>Loading datasets…</p>}

      {!loading && filtered.length === 0 && (
        <div className="empty-state">
          <p>No datasets match yet.</p>
          <p style={{ fontSize: 12 }}>Try clearing filters, or add your own file above.</p>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {filtered.map((d) => (
          <DatasetCard key={d.id} dataset={d} />
        ))}
      </div>
    </div>
  );
};
