import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, proxy API calls to the FastAPI backend so the client can use
// same-origin relative URLs (/api/...) and avoid CORS entirely.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
