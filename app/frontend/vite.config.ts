import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { cpSync, mkdirSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";

// Git symlinks can become plain text files on Windows. Stage real files so
// development and packaged builds both serve the shared images reliably.
const publicDir = fileURLToPath(new URL("./node_modules/.cache/sweety-public/", import.meta.url));
rmSync(publicDir, { recursive: true, force: true });
mkdirSync(publicDir, { recursive: true });
cpSync(fileURLToPath(new URL("../../web/images/", import.meta.url)), `${publicDir}/images`, { recursive: true });

export default defineConfig({
  publicDir,
  plugins: [react()],
  server: {
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8891",
    },
  },
});
