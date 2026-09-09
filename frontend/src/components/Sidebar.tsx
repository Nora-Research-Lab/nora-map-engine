import React from "react";
import { useWorkspace } from "../workspace/WorkspaceContext";
import type { PanelId } from "../types";

const ITEMS: { id: PanelId; label: string; icon: string }[] = [
  { id: "home", label: "Home", icon: "⌂" },
  { id: "datasets", label: "Datasets", icon: "▦" },
  { id: "layers", label: "Layers", icon: "☰" },
  { id: "tools", label: "Tools", icon: "◆" },
  { id: "export", label: "Export", icon: "↗" },
];

export const Sidebar: React.FC = () => {
  const { activePanel, setActivePanel, embed, layers } = useWorkspace();

  if (embed.readOnly) return null;

  return (
    <nav className="sidebar">
      {ITEMS.map((item) => (
        <button
          key={item.id}
          className={`sidebar-item ${activePanel === item.id ? "active" : ""}`}
          onClick={() => setActivePanel(activePanel === item.id ? null : item.id)}
          title={item.label}
        >
          <span className="sidebar-icon">{item.icon}</span>
          <span className="sidebar-label">{item.label}</span>
          {item.id === "layers" && layers.length > 0 && <span className="sidebar-badge">{layers.length}</span>}
        </button>
      ))}
    </nav>
  );
};
