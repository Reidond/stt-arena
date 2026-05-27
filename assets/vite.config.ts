import tailwindcss from "@tailwindcss/vite";
import { resolve } from "node:path";
import { defineConfig } from "vite";

const outDir = resolve(__dirname, "../src/stt_arena/static/dist");

export default defineConfig(({ mode }) => ({
  plugins: [tailwindcss()],
  base: mode === "production" ? "/static/dist/" : "/",
  build: {
    manifest: true,
    outDir,
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "src/main.ts"),
      },
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    cors: true,
    origin: "http://127.0.0.1:5173",
  },
}));
