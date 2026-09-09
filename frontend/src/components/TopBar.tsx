import React from "react";
import { IntentBar } from "./IntentBar";
import { useWorkspace } from "../workspace/WorkspaceContext";

export const TopBar: React.FC = () => {
  const { embed } = useWorkspace();
  if (embed.readOnly) return null;

  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark">◆</span>
        <span className="brand-name">NORA Map Engine</span>
      </div>
      <div className="topbar-intent">
        <IntentBar />
      </div>
    </header>
  );
};
