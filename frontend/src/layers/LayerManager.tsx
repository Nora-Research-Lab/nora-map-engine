import React, { useState } from "react";
import { useWorkspace } from "../workspace/WorkspaceContext";
import type { Layer } from "../types";
import * as api from "../services/api";

function LegendPreview({ layer }: { layer: Layer }) {
  const legend = layer.legend;
  if (!legend) return null;
  if (legend.type === "gradient" && legend.ramp) {
    return (
      <div className="legend-gradient" style={{ background: `linear-gradient(90deg, ${legend.ramp.join(",")})` }} />
    );
  }
  if (legend.type === "categorical" && legend.entries?.length) {
    return (
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
        {legend.entries.slice(0, 6).map((e) => (
          <span key={e.value} className="tag" style={{ borderColor: e.color }}>
            <span style={{ width: 8, height: 8, borderRadius: 4, background: e.color, display: "inline-block", marginRight: 4 }} />
            {e.value}
          </span>
        ))}
      </div>
    );
  }
  return <span style={{ width: 12, height: 12, borderRadius: 3, background: legend.color, display: "inline-block" }} />;
}

function LayerRow({ layer, index, total }: { layer: Layer; index: number; total: number }) {
  const { patchLayer, removeLayer, zoomToLayer, notify } = useWorkspace();
  const [expanded, setExpanded] = useState(false);

  const move = async (direction: -1 | 1) => {
    await patchLayer(layer.id, { order: layer.order + direction * 1.5 });
  };

  return (
    <div className="card layer-row">
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <input
          type="checkbox"
          checked={layer.visible}
          onChange={(e) => patchLayer(layer.id, { visible: e.target.checked })}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {layer.name}
          </div>
          <div style={{ fontSize: 11, color: "var(--ink-dim)" }}>{layer.render_type.replace("_", " ")}</div>
        </div>
        <button className="btn btn-ghost btn-sm" title="Move up" disabled={index === 0} onClick={() => move(1)}>▲</button>
        <button className="btn btn-ghost btn-sm" title="Move down" disabled={index === total - 1} onClick={() => move(-1)}>▼</button>
        <button className="btn btn-ghost btn-sm" title="Zoom to layer" onClick={() => zoomToLayer(layer)}>⌖</button>
        <button className="btn btn-ghost btn-sm" onClick={() => setExpanded((v) => !v)}>{expanded ? "–" : "⚙"}</button>
      </div>

      <div style={{ marginTop: 6 }}>
        <LegendPreview layer={layer} />
      </div>

      {expanded && (
        <div className="layer-config">
          <div className="divider" />
          <div className="label" style={{ marginBottom: 4 }}>How should this layer look?</div>
          <label style={{ fontSize: 12, display: "block", marginBottom: 6 }}>
            Opacity
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={layer.opacity}
              onChange={(e) => patchLayer(layer.id, { opacity: Number(e.target.value) })}
              style={{ width: "100%" }}
            />
          </label>

          {(layer.render_type === "circle" || layer.render_type === "proportional_circle") && (
            <label style={{ fontSize: 12, display: "block", marginBottom: 6 }}>
              Point color
              <input
                type="color"
                defaultValue={layer.style.color ?? "#c97c4a"}
                onChange={(e) => patchLayer(layer.id, { style_overrides: { color: e.target.value } })}
                style={{ width: "100%", height: 28 }}
              />
            </label>
          )}

          {layer.render_type === "line" && (
            <label style={{ fontSize: 12, display: "block", marginBottom: 6 }}>
              Line color
              <input
                type="color"
                defaultValue={layer.style.color ?? "#4fb6b0"}
                onChange={(e) => patchLayer(layer.id, { style_overrides: { color: e.target.value } })}
                style={{ width: "100%", height: 28 }}
              />
            </label>
          )}

          <label style={{ fontSize: 12, display: "block", marginBottom: 6 }}>
            Layer type
            <select
              value={layer.render_type}
              onChange={(e) => patchLayer(layer.id, { render_type: e.target.value as Layer["render_type"] })}
              style={{ width: "100%" }}
            >
              {["circle", "proportional_circle", "cluster", "heatmap"].includes(layer.render_type) && (
                <>
                  <option value="circle">Points</option>
                  <option value="cluster">Clustered points</option>
                  <option value="proportional_circle">Sized by value</option>
                  <option value="heatmap">Heatmap</option>
                </>
              )}
              {["line"].includes(layer.render_type) && <option value="line">Line</option>}
              {["fill", "choropleth"].includes(layer.render_type) && (
                <>
                  <option value="fill">Filled</option>
                  <option value="choropleth">Choropleth (by value)</option>
                </>
              )}
              {["raster", "hillshade"].includes(layer.render_type) && <option value="raster">Raster</option>}
            </select>
          </label>

          <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
            <a className="btn btn-sm" href={api.geojsonDownloadUrl(layer.dataset_id)} target="_blank" rel="noreferrer">
              GeoJSON
            </a>
            <a className="btn btn-sm" href={api.geotiffDownloadUrl(layer.dataset_id)} target="_blank" rel="noreferrer">
              GeoTIFF
            </a>
            <button
              className="btn btn-sm btn-danger"
              style={{ marginLeft: "auto" }}
              onClick={async () => { await removeLayer(layer.id); notify(`Removed "${layer.name}".`); }}
            >
              Remove
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export const LayerManager: React.FC = () => {
  const { layers } = useWorkspace();
  const sorted = [...layers].sort((a, b) => b.order - a.order);

  if (!sorted.length) {
    return (
      <div className="empty-state">
        <p>No layers on the map yet.</p>
        <p style={{ fontSize: 12 }}>Add a dataset from the Datasets panel to get started.</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {sorted.map((layer, i) => (
        <LayerRow key={layer.id} layer={layer} index={i} total={sorted.length} />
      ))}
    </div>
  );
};
