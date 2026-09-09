import React, { useState } from "react";
import { useWorkspace } from "../workspace/WorkspaceContext";
import * as api from "../services/api";

function composeAndDownloadPng(
  mapCanvas: HTMLCanvasElement,
  opts: { title: string; showLegend: boolean; showScale: boolean; showNorthArrow: boolean; attribution: string; layers: { name: string; color: string }[] }
) {
  const out = document.createElement("canvas");
  out.width = mapCanvas.width;
  out.height = mapCanvas.height;
  const ctx = out.getContext("2d")!;
  ctx.drawImage(mapCanvas, 0, 0);

  // Title banner
  if (opts.title) {
    ctx.fillStyle = "rgba(12,19,16,0.85)";
    ctx.fillRect(0, 0, out.width, 56);
    ctx.fillStyle = "#e8ede9";
    ctx.font = "600 22px 'Space Grotesk', sans-serif";
    ctx.fillText(opts.title, 20, 36);
  }

  // Legend box
  if (opts.showLegend && opts.layers.length) {
    const boxW = 220;
    const boxH = 24 + opts.layers.length * 20;
    const x = out.width - boxW - 20;
    const y = out.height - boxH - 20 - (opts.showScale ? 30 : 0);
    ctx.fillStyle = "rgba(12,19,16,0.85)";
    ctx.fillRect(x, y, boxW, boxH);
    ctx.strokeStyle = "#263831";
    ctx.strokeRect(x, y, boxW, boxH);
    ctx.fillStyle = "#e8ede9";
    ctx.font = "600 12px 'Space Grotesk', sans-serif";
    ctx.fillText("Legend", x + 12, y + 18);
    opts.layers.forEach((l, i) => {
      const ly = y + 34 + i * 20;
      ctx.fillStyle = l.color;
      ctx.fillRect(x + 12, ly - 9, 10, 10);
      ctx.fillStyle = "#c8d3ce";
      ctx.font = "12px 'Space Grotesk', sans-serif";
      ctx.fillText(l.name, x + 28, ly);
    });
  }

  // North arrow
  if (opts.showNorthArrow) {
    const cx = out.width - 40;
    const cy = 70;
    ctx.fillStyle = "#e8ede9";
    ctx.beginPath();
    ctx.moveTo(cx, cy - 16);
    ctx.lineTo(cx + 8, cy + 10);
    ctx.lineTo(cx, cy + 4);
    ctx.lineTo(cx - 8, cy + 10);
    ctx.closePath();
    ctx.fill();
    ctx.font = "600 11px 'Space Grotesk', sans-serif";
    ctx.fillText("N", cx - 4, cy - 20);
  }

  // Attribution
  ctx.fillStyle = "rgba(12,19,16,0.7)";
  ctx.font = "10px 'Space Grotesk', sans-serif";
  ctx.fillText(opts.attribution, 12, out.height - 10);

  out.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${opts.title || "map"}.png`;
    a.click();
    URL.revokeObjectURL(url);
  });
}

export const ExportPage: React.FC = () => {
  const { layers, mapRef, notify } = useWorkspace();
  const [title, setTitle] = useState("My Map");
  const [showLegend, setShowLegend] = useState(true);
  const [showScale, setShowScale] = useState(true);
  const [showNorthArrow, setShowNorthArrow] = useState(true);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const visibleLayers = layers.filter((l) => l.visible);

  const exportPng = () => {
    const map = mapRef.current;
    if (!map) return;
    const canvas = map.getCanvas();
    const legendLayers = visibleLayers.map((l) => ({
      name: l.name,
      color: (l.legend?.color as string) ?? l.legend?.ramp?.[Math.floor((l.legend.ramp.length - 1) / 2)] ?? "#c97c4a",
    }));
    composeAndDownloadPng(canvas, {
      title,
      showLegend,
      showScale,
      showNorthArrow,
      attribution: "© OpenStreetMap contributors · NORA Map Engine",
      layers: legendLayers,
    });
  };

  const createShareLink = async () => {
    const map = mapRef.current;
    if (!map) return;
    setSaving(true);
    try {
      const center = map.getCenter();
      const workspace = await api.createMap({
        name: title || "Untitled Map",
        view: { center: [center.lng, center.lat], zoom: map.getZoom(), bearing: map.getBearing(), pitch: map.getPitch() },
        layer_ids: layers.map((l) => l.id),
      });
      const url = `${window.location.origin}${window.location.pathname}?workspace=${workspace.id}`;
      setShareUrl(url);
      await navigator.clipboard.writeText(url).catch(() => {});
      notify("Share link copied to clipboard.");
    } catch (e: any) {
      notify(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="card" style={{ marginBottom: 10 }}>
        <div className="label" style={{ marginBottom: 8 }}>Create Map for Report</div>
        <label style={{ fontSize: 12, display: "block", marginBottom: 8 }}>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: "100%" }} />
        </label>
        <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
          <input type="checkbox" checked={showLegend} onChange={(e) => setShowLegend(e.target.checked)} /> Legend
        </label>
        <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
          <input type="checkbox" checked={showScale} onChange={(e) => setShowScale(e.target.checked)} /> Scale bar (shown on map)
        </label>
        <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <input type="checkbox" checked={showNorthArrow} onChange={(e) => setShowNorthArrow(e.target.checked)} /> North arrow
        </label>
        <button className="btn btn-primary btn-block" onClick={exportPng}>Export PNG</button>
      </div>

      <div className="card" style={{ marginBottom: 10 }}>
        <div className="label" style={{ marginBottom: 8 }}>Share this map</div>
        <p style={{ fontSize: 12, color: "var(--ink-dim)" }}>
          Saves the current view and layers, and gives you a link that reopens them.
        </p>
        <button className="btn btn-block" disabled={saving} onClick={createShareLink}>
          {saving ? "Saving…" : "Create Share Link"}
        </button>
        {shareUrl && (
          <input readOnly value={shareUrl} style={{ width: "100%", marginTop: 8, fontSize: 11 }} onFocus={(e) => e.target.select()} />
        )}
      </div>

      <div className="card">
        <div className="label" style={{ marginBottom: 8 }}>Download layer data</div>
        {visibleLayers.length === 0 && <p style={{ fontSize: 12, color: "var(--ink-dim)" }}>No visible layers.</p>}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {visibleLayers.map((l) => (
            <div key={l.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 12 }}>
              <span>{l.name}</span>
              <span style={{ display: "flex", gap: 4 }}>
                <a className="btn btn-sm" href={api.geojsonDownloadUrl(l.dataset_id)}>GeoJSON</a>
                <a className="btn btn-sm" href={api.geotiffDownloadUrl(l.dataset_id)}>GeoTIFF</a>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
