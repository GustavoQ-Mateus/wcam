import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const REPOSITORY_ROOT = fileURLToPath(new URL("..", import.meta.url));
const AGENT_URL = process.env.VITE_AGENT_URL ?? "http://127.0.0.1:8080";

export default defineConfig({
  plugins: [react()],
  server: {
    fs: { allow: [REPOSITORY_ROOT] },
    proxy: { "/api": { target: AGENT_URL, changeOrigin: true } },
  },
  build: { outDir: "dist" },
  test: { include: ["src/**/*.test.ts"] },
});
