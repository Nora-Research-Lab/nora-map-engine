import React from "react";
import { useWorkspace } from "../workspace/WorkspaceContext";

export const Toast: React.FC = () => {
  const { toast } = useWorkspace();
  if (!toast) return null;
  return <div className="toast panel">{toast}</div>;
};
