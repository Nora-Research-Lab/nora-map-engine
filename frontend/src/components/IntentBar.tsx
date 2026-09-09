import React, { useState } from "react";
import { useWorkspace } from "../workspace/WorkspaceContext";
import * as api from "../services/api";

const SUGGESTIONS = [
  "I want to see gold occurrences",
  "Compare geology and magnetic data",
  "Visualize elevation",
  "Create a heatmap of occurrences",
];

export const IntentBar: React.FC = () => {
  const { setActivePanel, notify, addDatasetToMap, patchLayer, layers } = useWorkspace();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (value: string) => {
    if (!value.trim() || busy) return;
    setBusy(true);
    try {
      const result = await api.interpretIntent(value);
      notify(result.hint);
      setActivePanel(result.panel);

      if (result.tool === "heatmap") {
        const target = layers.find((l) => result.matched_datasets.some((d) => d.id === l.dataset_id)) ?? layers[0];
        if (target) await patchLayer(target.id, { render_type: "heatmap" });
      } else if (result.matched_datasets.length && result.panel === "datasets") {
        // Surface matches but let the user pick "Add to Map" themselves --
        // we never add data to the map without an explicit action.
      }
    } catch (e: any) {
      notify(e.message ?? "Couldn't interpret that.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="intent-bar panel">
      <input
        className="intent-input"
        placeholder="What do you want to see? e.g. “compare geology and magnetic data”"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit(text);
        }}
      />
      <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => submit(text)}>
        {busy ? "…" : "Go"}
      </button>
      <div className="intent-suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="tag intent-chip" onClick={() => { setText(s); submit(s); }}>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
};
