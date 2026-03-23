#!/usr/bin/env node
/**
 * Inject favicon link into webrtc_ui index.html so /favicon.svg is used (Vite copies public/).
 */
const fs = require("fs");
const path = "index.html";
let s = fs.readFileSync(path, "utf8");
if (s.includes('href="/favicon.svg"') || s.includes("href='/favicon.svg'")) {
  console.log("index.html: favicon link already present");
  process.exit(0);
}
const link =
  '<link rel="icon" type="image/svg+xml" href="/favicon.svg" />\n    ';
if (s.includes("<head>")) {
  s = s.replace("<head>", "<head>\n    " + link.trim() + "\n    ");
} else if (s.includes("<head ")) {
  s = s.replace(/<head[^>]*>/, (m) => m + "\n    " + link.trim() + "\n    ");
} else {
  console.error("patch-index-favicon: no <head> in index.html");
  process.exit(1);
}
fs.writeFileSync(path, s);
console.log("index.html: injected favicon link -> /favicon.svg");
