import React from "react";
import { WorkspaceProvider, useWorkspace } from "./workspace/WorkspaceContext";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { PanelDrawer } from "./components/PanelDrawer";
import { Toast } from "./components/Toast";
import { MapView } from "./map/MapView";

const Shell: React.FC = () => {
  const { error, setError } = useWorkspace();
  return (
    <div className="app-shell">
      <TopBar />
      <div className="app-body">
        <Sidebar />
        <main className="map-area">
          <MapView />
          <PanelDrawer />
        </main>
      </div>
      <Toast />
      {error && (
        <div className="toast panel" style={{ borderColor: "var(--danger)" }}>
          {error}
          <button className="btn btn-ghost btn-sm" onClick={() => setError(null)}>✕</button>
        </div>
      )}
    </div>
  );
};

export default function App() {
  return (
    <WorkspaceProvider>
      <Shell />
    </WorkspaceProvider>
  );
}
