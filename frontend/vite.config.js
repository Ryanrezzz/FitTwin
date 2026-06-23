import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// In dev we proxy /api to the FastAPI backend so the browser sees one origin
// (no CORS dance). In prod, set VITE_API_BASE_URL to the API's public URL.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
