import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The browser calls /api/...; Vite forwards those requests to FastAPI.
// Same origin for the browser means no CORS setup is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // listen on all interfaces so Docker can expose the port
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.API_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
