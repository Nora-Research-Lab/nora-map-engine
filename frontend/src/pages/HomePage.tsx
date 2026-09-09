import React from "react";
import { useWorkspace } from "../workspace/WorkspaceContext";

const CATEGORIES = [
  { tag: "geology", label: "Geology" },
  { tag: "gold", label: "Mineral exploration" },
  { tag: "environment", label: "Environment" },
  { tag: "rivers", label: "Hydrology" },
  { tag: "dem", label: "Terrain" },
];

export const HomePage: React.FC = () => {
  const { setActivePanel, workspaces, layers } = useWorkspace();
  const demo = workspaces.find((w) => w.name === "Gold Exploration Demo");

  return (
    <div>
      <p style={{ fontSize: 13, color: "var(--ink-dim)", lineHeight: 1.5 }}>
        NORA Map Engine turns geological, environmental, geophysical, and terrain
        datasets into interactive maps — no GIS knowledge required.
      </p>

      <div className="card" style={{ marginTop: 12 }}>
        <div className="label" style={{ marginBottom: 8 }}>What are you working with?</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {CATEGORIES.map((c) => (
            <button key={c.tag} className="tag" style={{ cursor: "pointer" }} onClick={() => setActivePanel("datasets")}>
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div className="label" style={{ marginBottom: 6 }}>Get started in 3 steps</div>
        <ol style={{ fontSize: 13, color: "var(--ink-dim)", paddingLeft: 18, margin: 0, lineHeight: 1.9 }}>
          <li>Add a dataset (upload one, paste a URL, or pick one from the library)</li>
          <li>We recommend how it should look — add it to the map</li>
          <li>Layer more data, run a tool, then export or share your map</li>
        </ol>
        <button className="btn btn-primary btn-block" style={{ marginTop: 10 }} onClick={() => setActivePanel("datasets")}>
          Browse Datasets
        </button>
      </div>

      {demo && layers.length > 0 && (
        <div className="card" style={{ marginTop: 12 }}>
          <div className="label" style={{ marginBottom: 4 }}>Demo workspace loaded</div>
          <p style={{ fontSize: 12, color: "var(--ink-dim)", margin: "0 0 8px" }}>
            "{demo.name}" — {layers.length} layer(s) already on the map. Open Layers to explore them.
          </p>
          <button className="btn btn-sm" onClick={() => setActivePanel("layers")}>Open Layers</button>
        </div>
      )}
    </div>
  );
};
