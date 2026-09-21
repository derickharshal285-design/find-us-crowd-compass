"use strict";
// Bundles the multi-file website into ONE self-contained HTML with inline
// CSS + JS (works from file://, GitHub Pages, any static host).
//   node website/build-single.js website docs/index.html
const fs = require("fs");
const path = require("path");

const [, , srcDir = "website", outFile = "docs/index.html"] = process.argv;

function read(p) { return fs.readFileSync(path.join(process.cwd(), p), "utf8"); }

let html = read(path.join(srcDir, "index.html"));

// 1) inline stylesheet
const css = read(path.join(srcDir, "styles.css"));
html = html.replace('<link rel="stylesheet" href="styles.css">',
  () => "<style>\n" + css + "\n</style>");

// 2) inline scripts in order (concepts must precede app.js at runtime)
for (const js of ["concepts.js", "app.js", "sims.js"]) {
  const body = read(path.join(srcDir, js));
  // NOTE: replacement must be a FUNCTION — a string replacement would expand
  // every "$$" in the script body into "$" (String.prototype.replace rule).
  html = html.replace('<script src="' + js + '"></script>',
    () => "<script>\n" + body + "\n</script>");
}

// 3) repo artifacts are outside the served /docs folder → link to GitHub raw
const RAW = "https://raw.githubusercontent.com/derickharshal285-design/find-us-crowd-compass/main/";
html = html.replace(/href="\.\.\/research\/([^"]+)"( download)?/g,
  (m, p) => 'href="' + RAW + "research/" + p + '" target="_blank" rel="noopener" download');

fs.writeFileSync(outFile, html);
console.log(outFile + "  " + (fs.statSync(outFile).size / 1024).toFixed(1) + " KB");
console.log("inline script/stylesheet remaining <script src>/<link> = " +
  (html.match(/<script src=<|src="[a-z]+\.(js|css)"/g) || []).length);