// smoke_report.mjs — headless render test for .ai/report.html
// Executes the self-contained report in jsdom and asserts it actually renders
// (vendored markdown-it / DOMPurify / highlight.js load, Docs + Insights views
// populate, no uncaught runtime errors). Run: node tools/smoke_report.mjs [path]
import fs from "node:fs";
import { JSDOM } from "jsdom";

const path = process.argv[2] || ".ai/report.html";
const html = fs.readFileSync(path, "utf8");
const errors = [];

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  pretendToBeVisual: true,
  beforeParse(window) {
    window.IntersectionObserver = class { observe() {} disconnect() {} unobserve() {} };
    if (!window.matchMedia) window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
    if (window.HTMLDialogElement) {
      window.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
      window.HTMLDialogElement.prototype.close = function () { this.open = false; };
    }
    window.onerror = (m) => errors.push(String(m));
    window.addEventListener("error", (e) => errors.push(String(e.error || e.message)));
  },
});
const { window } = dom;
const doc = window.document;

let fails = 0;
const ok = (cond, msg) => { if (cond) { console.log("  ok   " + msg); } else { console.error("  FAIL " + msg); fails++; } };
const nav = (hash) => { window.location.hash = hash; window.dispatchEvent(new window.HashChangeEvent("hashchange")); };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

await wait(60);

console.log("library globals:");
ok(!!window.markdownit, "markdown-it loaded");
ok(!!window.DOMPurify, "DOMPurify loaded");
ok(!!window.hljs, "highlight.js loaded");
ok(typeof window.cytoscape === "function", "Cytoscape (Map graph lib) loaded — inlined, not CDN");

console.log("load + Docs (overview):");
ok(errors.length === 0, "no uncaught errors on load" + (errors.length ? " — " + errors.join(" | ") : ""));
ok(/DeepInit/.test(doc.querySelector(".brand")?.textContent || ""), "co-branded masthead renders");
const content = doc.querySelector("#content");
ok(!!content && content.textContent.trim().length > 50, "overview content renders");
ok(doc.body.classList.contains("mode-docs"), "defaults to Docs mode");
ok(doc.querySelectorAll(".navlink .ni svg").length > 0, "left-rail SVG icons render");

console.log("Insights:");
nav("#insights"); await wait(20);
ok(doc.body.classList.contains("mode-insights"), "switches to Insights mode");
ok(doc.querySelectorAll(".kpi").length >= 4, "KPI cards render");
ok(!!doc.querySelector(".donutwrap svg"), "severity donut SVG renders");
ok(doc.querySelectorAll(".irow").length > 0, "issue triage rows render");
ok(!!doc.querySelector(".dtable"), "decisions table renders");
ok(!!doc.querySelector('a[href="#map"]'), "Insights links to the interactive Map view");
ok(Array.prototype.some.call(doc.querySelectorAll(".card2 h3"), (h) => /Component dependency graph/.test(h.textContent)), "component graph card renders (honest-degrade or populated)");

console.log("component page (markdown-it path):");
const data = JSON.parse(doc.getElementById("deepinit-data").textContent);
const comp = (data.components[0] || {}).anchor;
if (comp) {
  nav("#" + comp); await wait(20);
  ok(doc.body.classList.contains("mode-docs"), "returns to Docs mode on a component");
  ok(content.textContent.trim().length > 50, "component body renders via markdown-it");
}

console.log("command palette:");
ok(!!doc.getElementById("cmdk"), "palette present");

console.log("shortcuts dialog — discoverable close (reported stuck-dialog fix):");
try {
  const dlg = doc.getElementById("shortcuts");
  ok(!!doc.getElementById("shortcuts-x"), "dialog has a visible × close button");
  dlg.showModal(); ok(dlg.open === true, "dialog opens");
  doc.getElementById("shortcuts-x").dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
  ok(dlg.open === false, "× button closes the dialog");
  dlg.showModal(); dlg.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
  ok(dlg.open === false, "backdrop click closes the dialog");
} catch (e) { ok(false, "dialog-close test threw: " + e.message); }

console.log("XSS safety (markdown-it html:false + DOMPurify):");
try {
  const md = window.markdownit({ html: false, linkify: true });
  const payload = "<script>window.PWNED=1<\/script>\n\n[x](javascript:alert(1))\n\n<img src=x onerror=alert(2)>";
  const clean = window.DOMPurify.sanitize(md.render(payload));
  const probe = doc.createElement("div"); probe.innerHTML = clean; // 'clean' is already sanitized
  const liveScript = probe.querySelectorAll("script").length > 0;
  const liveOnerror = !!probe.querySelector("[onerror]");
  const jsHref = Array.prototype.some.call(probe.querySelectorAll("a[href]"), (a) => /^(javascript|vbscript):/i.test(a.getAttribute("href") || ""));
  ok(!liveScript && !liveOnerror && !jsHref, "no live <script>/onerror/js-href in sanitized DOM");
  ok(!window.PWNED, "no script executed from payload");
} catch (e) { ok(false, "xss test threw: " + e.message); }

console.log("component graph (populated SVG render path):");
try {
  // Inject a populated dashboard.graph into a clone of the report's data island and re-render in a
  // second jsdom — exercises the SVG drawing path (the dogfood report itself honest-degrades, no graph).
  const d2 = JSON.parse(doc.getElementById("deepinit-data").textContent);
  d2.dashboard = d2.dashboard || {};
  d2.dashboard.graph = { available: true,
    nodes: [{ id: "auth", anchor: "c-auth", files: 3, exports: 4, in_deg: 0, out_deg: 1, risk: 0.8, criticality: "Core", x: 0, y: -120 },
            { id: "billing", anchor: "c-billing", files: 2, exports: 2, in_deg: 0, out_deg: 1, risk: null, criticality: "", x: 104, y: 60 },
            { id: "core", anchor: "c-core", files: 5, exports: 9, in_deg: 2, out_deg: 0, risk: 0.2, criticality: "Core", x: -104, y: 60 }],
    edges: [{ from: "auth", to: "core", weight: 2, dir: "out" }, { from: "billing", to: "core", weight: 1, dir: "out" }] };
  const island = JSON.stringify(d2).replace(/</g, "\\u003c").replace(/>/g, "\\u003e");
  const html2 = html.replace(/(<script\b[^>]*\bid="deepinit-data"[^>]*>)[\s\S]*?(<\/script>)/, (_m, a, b) => a + island + b);
  const dom2 = new JSDOM(html2, {
    runScripts: "dangerously", pretendToBeVisual: true,
    beforeParse(w) {
      w.IntersectionObserver = class { observe() {} disconnect() {} unobserve() {} };
      if (!w.matchMedia) w.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
    },
  });
  await wait(60);
  const doc2 = dom2.window.document;
  dom2.window.location.hash = "#insights";
  dom2.window.dispatchEvent(new dom2.window.HashChangeEvent("hashchange"));
  await wait(20);
  const svg = doc2.querySelector("svg.depgraph");
  ok(!!svg, "populated graph renders an inline SVG (no off-host img)");
  ok(svg && svg.querySelectorAll("circle").length >= 3, "graph nodes render as SVG circles (3)");
  ok(svg && svg.querySelectorAll("line").length >= 2, "graph edges render as SVG lines (2)");

  // Map view — interactive, navigable component graph (ADR-024). In jsdom the canvas has no layout, so the
  // first-party SVG fallback renders (data-node-id per node); a real browser uses Cytoscape. We assert the
  // DOM/event/navigation wiring (not pixels): switching to Map renders nodes, and a node-click navigates.
  console.log("Map view (navigable component graph — ADR-024):");
  dom2.window.location.hash = "#map";
  dom2.window.dispatchEvent(new dom2.window.HashChangeEvent("hashchange"));
  await wait(40); // viewMap defers graph init via setTimeout(0)
  ok(doc2.body.classList.contains("mode-map"), "switching to #map enters Map mode");
  ok(!!doc2.getElementById("tab-map"), "Map tab present in the tablist");
  ok(doc2.querySelectorAll('.viewswitch [role="tab"]').length === 3, "three top-level tabs (Docs/Insights/Map)");
  const mnodes = doc2.querySelectorAll(".mapwrap [data-node-id]");
  ok(mnodes.length >= 3, "Map renders a navigable element per node (data-node-id; SVG fallback in jsdom)");
  const target = doc2.querySelector('.mapwrap [data-node-id="auth"]') || mnodes[0];
  const nid = target.getAttribute("data-node-id");
  target.dispatchEvent(new dom2.window.MouseEvent("click", { bubbles: true }));
  await wait(20);
  ok(dom2.window.location.hash === "#c-" + nid, "clicking a Map node navigates to #c-<component> (" + dom2.window.location.hash + ")");
  ok(doc2.body.classList.contains("mode-docs"), "node-click lands on the component's Docs page");
  // Layout regression tripwire (jsdom has no layout engine, so assert the CSS invariant by text): the Map's
  // <main> must span ALL grid tracks, else body.no-toc restores a rail column and the graph is crushed into ~17rem.
  ok(/mode-map main\{[^}]*grid-column:1\/-1/.test(html), "Map view spans all grid columns (full-bleed, not the narrow rail column)");
} catch (e) { ok(false, "populated-graph / Map render threw: " + e.message); }

console.log("Map honest-degrade (graph.available=false — R1):");
try {
  const d3 = JSON.parse(doc.getElementById("deepinit-data").textContent);
  d3.dashboard = d3.dashboard || {};
  d3.dashboard.graph = { available: false, nodes: [], edges: [] };
  const island3 = JSON.stringify(d3).replace(/</g, "\\u003c").replace(/>/g, "\\u003e");
  const html3 = html.replace(/(<script\b[^>]*\bid="deepinit-data"[^>]*>)[\s\S]*?(<\/script>)/, (_m, a, b) => a + island3 + b);
  const dom3 = new JSDOM(html3, {
    runScripts: "dangerously", pretendToBeVisual: true,
    beforeParse(w) {
      w.IntersectionObserver = class { observe() {} disconnect() {} unobserve() {} };
      if (!w.matchMedia) w.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
    },
  });
  await wait(60);
  const doc3 = dom3.window.document;
  dom3.window.location.hash = "#map";
  dom3.window.dispatchEvent(new dom3.window.HashChangeEvent("hashchange"));
  await wait(40);
  ok(!!doc3.querySelector(".mapwrap .unavail"), "Map shows the honest 'graph unavailable' state when graph.available=false");
  ok(!doc3.querySelector(".mapwrap [data-node-id]"), "no fabricated Map nodes in the unavailable state (R1)");
} catch (e) { ok(false, "Map honest-degrade test threw: " + e.message); }

console.log("i18n chrome localization + RTL (he):");
try {
  // build_i18n sets <html lang dir> server-side; here we simulate that on the EN render and assert the
  // template's STRINGS/T() chrome localizes to Hebrew + the document goes RTL (the client-side half).
  const htmlHe = html.replace(/<html\b[^>]*>/, '<html lang="he" dir="rtl" data-theme="auto">');
  const domHe = new JSDOM(htmlHe, {
    runScripts: "dangerously", pretendToBeVisual: true,
    beforeParse(w) {
      w.IntersectionObserver = class { observe() {} disconnect() {} unobserve() {} };
      if (!w.matchMedia) w.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
    },
  });
  await wait(60);
  const docHe = domHe.window.document;
  ok(docHe.documentElement.getAttribute("dir") === "rtl", "html dir=rtl for he");
  const docsTab = docHe.querySelector("#tab-docs");
  ok(docsTab && /תיעוד/.test(docsTab.textContent), "tabs localized to Hebrew (chrome STRINGS picked by <html lang>)");
  const railText = (docHe.querySelector("#rail") || {}).textContent || "";
  ok(/סקירה/.test(railText) && /רכיבים/.test(railText), "rail nav localized to Hebrew (overview + components)");
} catch (e) { ok(false, "he chrome/RTL render threw: " + e.message); }

console.log(fails ? `\nSMOKE: ${fails} FAILURE(S)` : "\nSMOKE: ALL PASS");
process.exit(fails ? 1 : 0);
