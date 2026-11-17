import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Team B dashboard backend (encounters, auth, SOAP, PDF, FHIR)
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
      // Our NVIDIA transcription service (realtime WebSocket + consultations)
      "/test": {
        target: "http://127.0.0.1:8003",
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
});
