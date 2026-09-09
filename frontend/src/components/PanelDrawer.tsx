import React from "react";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { HomePage } from "../pages/HomePage";
import { DatasetLibrary } from "../datasets/DatasetLibrary";
import { LayerManager } from "../layers/LayerManager";
import { ToolsPanel } from "../tools/ToolsPanel";
import { ExportPage } from "../pages/ExportPage";

const TITLES: Record<string, string> = {
  home: "Home",
  datasets: "Datasets",
  layers: "Layers",
  tools: "Tools",
  export: "Export",
};

export const PanelDrawer: React.FC = () => {
  const { activePanel, setActivePanel, embed } = useWorkspace();
  if (!activePanel || embed.readOnly) return null;

  return (
    <aside className="panel-drawer panel">
      <div className="panel-drawer-header">
        <span style={{ fontWeight: 600 }}>{TITLES[activePanel]}</span>
        <button className="btn btn-ghost btn-sm" onClick={() => setActivePanel(null)}>✕</button>
      </div>
      <div className="panel-drawer-body scroll-y">
        {activePanel === "home" && <HomePage />}
        {activePanel === "datasets" && <DatasetLibrary />}
        {activePanel === "layers" && <LayerManager />}
        {activePanel === "tools" && <ToolsPanel />}
        {activePanel === "export" && <ExportPage />}
      </div>
    </aside>
  );
};
