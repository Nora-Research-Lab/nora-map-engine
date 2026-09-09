import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Local dev: `npm run dev` runs Vite on :5173 and proxies /api to the
// FastAPI backend on :8000 (run separately with `uvicorn app.main:app --reload`).
// In production, the backend serves the built `dist/` directly (see
// backend/app/main.py), so no proxy is needed there.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
