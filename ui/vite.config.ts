import { lingui } from "@lingui/vite-plugin";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    // Must run before react(): generates src/routeTree.gen.ts from src/routes/.
    tanstackRouter({ target: "react", autoCodeSplitting: true }),
    react({ babel: { plugins: ["@lingui/babel-plugin-lingui-macro"] } }),
    lingui(),
    tailwindcss(),
  ],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  server: {
    port: 5173,
    // Polling is needed for file watching inside Docker on Windows hosts.
    watch: { usePolling: process.env.VITE_USE_POLLING === "true" },
  },
});
