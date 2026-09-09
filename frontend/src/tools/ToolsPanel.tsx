import React, { useState } from "react";
import { useWorkspace } from "../workspace/WorkspaceContext";
import * as api from "../services/api";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card" style={{ marginBottom: 8 }}>
      <button className="btn btn-ghost btn-block" style={{ justifyContent: "space-between" }} onClick={() => setOpen((v) => !v)}>
        <span>{title}</span>
        <span>{open ? "–" : "+"}</span>
      </button>
      {open && <div style={{ marginTop: 10 }}>{children}</div>}
    </div>
  );
}

export const ToolsPanel: React.FC = () => {
  const { datasets, layers, refreshDatasets, refreshLayers, notify, measureMode, setMeasureMode, patchLayer } = useWorkspace();
  const materialized = datasets.filter((d) => d.materialized);
  const rasters = materialized.filter((d) => d.kind === "raster");
  const vectors = materialized.filter((d) => d.kind === "vector");
  const demRasters = rasters.filter((d) => d.tags.includes("dem")).length ? rasters.filter((d) => d.tags.includes("dem")) : rasters;

  const [busy, setBusy] = useState(false);

  const [hillshadeDs, setHillshadeDs] = useState("");
  const [azimuth, setAzimuth] = useState(315);
  const [altitude, setAltitude] = useState(45);

  const [slopeDs, setSlopeDs] = useState("");
  const [slopeUnits, setSlopeUnits] = useState<"degrees" | "percent">("degrees");

  const [aspectDs, setAspectDs] = useState("");

  const [bufferDs, setBufferDs] = useState("");
  const [bufferDist, setBufferDist] = useState(500);

  const [clipDs, setClipDs] = useState("");
  const [clipMaskDs, setClipMaskDs] = useState("");

  const [reprojDs, setReprojDs] = useState("");
  const [targetCrs, setTargetCrs] = useState("EPSG:3857");

  const [calcA, setCalcA] = useState("");
  const [calcB, setCalcB] = useState("");
  const [expr, setExpr] = useState("A - B");

  const [heatmapLayerId, setHeatmapLayerId] = useState("");

  const after = async (msg: string) => {
    await Promise.all([refreshDatasets(), refreshLayers()]);
    notify(msg);
  };

  const run = async (fn: () => Promise<{ message: string }>) => {
    setBusy(true);
    try {
      const result = await fn();
      await after(result.message);
    } catch (e: any) {
      notify(e.hint ? `${e.message} ${e.hint}` : e.message);
    } finally {
      setBusy(false);
    }
  };

  const pointLayers = layers.filter((l) => ["circle", "proportional_circle", "cluster", "heatmap"].includes(l.render_type));

  return (
    <div>
      <Section title="Measure">
        <p style={{ fontSize: 12, color: "var(--ink-dim)" }}>Click points on the map, then double-click to finish.</p>
        <div style={{ display: "flex", gap: 6 }}>
          <button className={`btn btn-sm ${measureMode === "distance" ? "btn-primary" : ""}`} onClick={() => setMeasureMode(measureMode === "distance" ? null : "distance")}>
            Distance
          </button>
          <button className={`btn btn-sm ${measureMode === "area" ? "btn-primary" : ""}`} onClick={() => setMeasureMode(measureMode === "area" ? null : "area")}>
            Area
          </button>
        </div>
      </Section>

      <Section title="Create Heatmap">
        <p style={{ fontSize: 12, color: "var(--ink-dim)" }}>Switch a point layer to a density heatmap.</p>
        <select value={heatmapLayerId} onChange={(e) => setHeatmapLayerId(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
          <option value="">Choose a point layer…</option>
          {pointLayers.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
        <button
          className="btn btn-primary btn-sm btn-block"
          disabled={!heatmapLayerId || busy}
          onClick={async () => {
            setBusy(true);
            try {
              await patchLayer(heatmapLayerId, { render_type: "heatmap" });
              notify("Switched to a density heatmap.");
            } finally {
              setBusy(false);
            }
          }}
        >
          Apply Heatmap
        </button>
      </Section>

      <Section title="Terrain: Hillshade">
        <select value={hillshadeDs} onChange={(e) => setHillshadeDs(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
          <option value="">Choose an elevation dataset…</option>
          {demRasters.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <label style={{ fontSize: 12 }}>Azimuth ({azimuth}°)
          <input type="range" min={0} max={360} value={azimuth} onChange={(e) => setAzimuth(Number(e.target.value))} style={{ width: "100%" }} />
        </label>
        <label style={{ fontSize: 12 }}>Altitude ({altitude}°)
          <input type="range" min={0} max={90} value={altitude} onChange={(e) => setAltitude(Number(e.target.value))} style={{ width: "100%" }} />
        </label>
        <button className="btn btn-primary btn-sm btn-block" style={{ marginTop: 8 }} disabled={!hillshadeDs || busy}
          onClick={() => run(() => api.processHillshade(hillshadeDs, azimuth, altitude))}>
          Create Hillshade
        </button>
      </Section>

      <Section title="Terrain: Slope">
        <select value={slopeDs} onChange={(e) => setSlopeDs(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
          <option value="">Choose an elevation dataset…</option>
          {demRasters.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <select value={slopeUnits} onChange={(e) => setSlopeUnits(e.target.value as any)} style={{ width: "100%", marginBottom: 8 }}>
          <option value="degrees">Degrees</option>
          <option value="percent">Percent</option>
        </select>
        <button className="btn btn-primary btn-sm btn-block" disabled={!slopeDs || busy} onClick={() => run(() => api.processSlope(slopeDs, slopeUnits))}>
          Create Slope Map
        </button>
      </Section>

      <Section title="Terrain: Aspect">
        <select value={aspectDs} onChange={(e) => setAspectDs(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
          <option value="">Choose an elevation dataset…</option>
          {demRasters.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <button className="btn btn-primary btn-sm btn-block" disabled={!aspectDs || busy} onClick={() => run(() => api.processAspect(aspectDs))}>
          Create Aspect Map
        </button>
      </Section>

      <Section title="Buffer">
        <select value={bufferDs} onChange={(e) => setBufferDs(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
          <option value="">Choose a vector dataset…</option>
          {vectors.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <label style={{ fontSize: 12 }}>Distance (metres)
          <input type="number" value={bufferDist} min={1} onChange={(e) => setBufferDist(Number(e.target.value))} style={{ width: "100%" }} />
        </label>
        <button className="btn btn-primary btn-sm btn-block" style={{ marginTop: 8 }} disabled={!bufferDs || busy}
          onClick={() => run(() => api.processBuffer(bufferDs, bufferDist))}>
          Create Buffer
        </button>
      </Section>

      <Section title="Clip">
        <select value={clipDs} onChange={(e) => setClipDs(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
          <option value="">Dataset to clip…</option>
          {vectors.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <select value={clipMaskDs} onChange={(e) => setClipMaskDs(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
          <option value="">Clip to (boundary)…</option>
          {vectors.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <button className="btn btn-primary btn-sm btn-block" disabled={!clipDs || !clipMaskDs || busy}
          onClick={() => run(() => api.processClip(clipDs, clipMaskDs))}>
          Clip
        </button>
      </Section>

      <Section title="Reproject">
        <select value={reprojDs} onChange={(e) => setReprojDs(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
          <option value="">Choose a vector dataset…</option>
          {vectors.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <input placeholder="EPSG:3857" value={targetCrs} onChange={(e) => setTargetCrs(e.target.value)} style={{ width: "100%", marginBottom: 8 }} />
        <button className="btn btn-primary btn-sm btn-block" disabled={!reprojDs || busy} onClick={() => run(() => api.processReproject(reprojDs, targetCrs))}>
          Reproject
        </button>
      </Section>

      <Section title="Raster Calculator">
        <select value={calcA} onChange={(e) => setCalcA(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
          <option value="">Band A…</option>
          {rasters.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <select value={calcB} onChange={(e) => setCalcB(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
          <option value="">Band B (optional)…</option>
          {rasters.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <input value={expr} onChange={(e) => setExpr(e.target.value)} style={{ width: "100%", marginBottom: 8 }} />
        <p style={{ fontSize: 11, color: "var(--ink-faint)" }}>Use A and B, numbers, and + - * / ( )</p>
        <button className="btn btn-primary btn-sm btn-block" disabled={!calcA || busy}
          onClick={() => run(() => api.processRasterCalculator(calcA, calcB || null, expr))}>
          Compute
        </button>
      </Section>
    </div>
  );
};
