#!/usr/bin/env node
/**
 * NVIDIA webrtc_ui vite.config.ts targets es2020 — top-level await in config.ts
 * needs es2022+ / esnext. Injected during Docker build before `npm run build`.
 */
const fs = require("fs");
const path = "vite.config.ts";
let s = fs.readFileSync(path, "utf8");
if (/target:\s*["']esnext["']/.test(s) || /target:\s*["']es2022["']/.test(s)) {
  console.log("vite.config.ts: build.target already allows top-level await");
  process.exit(0);
}
const needle = "export default defineConfig({";
if (!s.includes(needle)) {
  console.error("patch-webrtc-vite: expected", JSON.stringify(needle), "in vite.config.ts");
  process.exit(1);
}
s = s.replace(
  needle,
  `export default defineConfig({
  build: {
    target: "esnext",
  },`,
);
fs.writeFileSync(path, s);
console.log("vite.config.ts: injected build.target esnext (for top-level await in config.ts)");
