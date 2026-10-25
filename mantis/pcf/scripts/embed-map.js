// Copies the built map page into the component: MantisMap/generated/map.ts
// Usage: node scripts/embed-map.js [path/to/Mantis_Sunshine.html]
const fs = require("fs");
const path = require("path");

const src = path.resolve(__dirname, "..", process.argv[2] || "../out/Mantis_Sunshine.html");
const html = fs.readFileSync(src, "utf8");
if (!html.includes("<head>")) throw new Error(`${src} has no <head> to add the embed settings to`);
const out = path.resolve(__dirname, "../MantisMap/generated/map.ts");
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, `// Generated from ${path.basename(src)} - do not edit\nexport const MAP_HTML = ${JSON.stringify(html)};\n`);
console.log(`embedded ${path.basename(src)} (${(html.length / 1e6).toFixed(2)} MB)`);
