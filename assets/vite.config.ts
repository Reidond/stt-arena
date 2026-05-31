import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { defineConfig } from "vite";

const outDir = resolve(__dirname, "../src/stt_arena/static/dist");

const viteDevOrigin =
  process.env.VITE_DEV_ORIGIN ?? "http://127.0.0.1:8000";

export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  base: mode === "production" ? "/static/dist/" : "/",
  build: {
    manifest: true,
    outDir,
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "src/main.tsx"),
      },
    },
  },
  server: {
    allowedHosts: ["vite", "localhost", "127.0.0.1"],
    // Reflect the requesting backend origin (localhost vs 127.0.0.1 both work).
    cors: true,
    // Absolute asset URLs in dev CSS/modules should target the Vite server.
    origin: viteDevOrigin,
  },
}));
