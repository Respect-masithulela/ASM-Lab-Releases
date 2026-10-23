// Headless ASM Lab solve: loads ASM Lab's own bundled code (actions + store modules from the installed app.asar, extracted),
// puts a project (.asmlab.json, the format ASM Lab saves) into its stores, runs its own solveActive (Solve F5 = aero, or
// aero + thermal), and writes the solved project (collections with Q, dP, rho, ... per tunnel, duct network with results).
//
// Usage: node asm_run.mjs <extracted app assets dir> <project.asmlab.json> <aero|both> <out.asmlab.json>
import fs from "node:fs"; import path from "node:path"; import { pathToFileURL } from "node:url";
const [assets, projPath, mode, outPath] = process.argv.slice(2);
const noop = () => {};
const el = () => new Proxy(function () {}, { get: (t, k) => (k === Symbol.toPrimitive ? () => "" : el()), apply: () => el(), construct: () => el() });
Object.assign(globalThis, { window: globalThis, self: globalThis, requestAnimationFrame: (f) => setTimeout(f, 0), cancelAnimationFrame: noop,
  addEventListener: noop, removeEventListener: noop, dispatchEvent: noop,
  matchMedia: () => ({ matches: false, addEventListener: noop, removeEventListener: noop }),
  CustomEvent: class { constructor(t, o) { this.type = t; this.detail = o?.detail; } } });
globalThis.document = { createElement: () => el(), addEventListener: noop, removeEventListener: noop, body: el(), documentElement: el(), querySelector: () => null, createElementNS: () => el() };
globalThis.localStorage = { getItem: () => null, setItem: noop, removeItem: noop }; globalThis.sessionStorage = globalThis.localStorage;
// no Worker: ASM Lab then runs the same solver synchronously in this thread
delete globalThis.Worker;

const find = (re) => fs.readdirSync(assets).find((f) => re.test(f));
const actions = await import(pathToFileURL(path.join(assets, find(/^actions-.*\.js$/))).href);
const storeMod = await import(pathToFileURL(path.join(assets, find(/^store-.*\.js$/))).href);
const app = Object.values(actions).find((v) => typeof v === "function" && v.getState && "solveActive" in v.getState());
const ductStore = Object.values(storeMod).find((v) => typeof v === "function" && v.getState && "data" in v.getState() && "results" in v.getState());

const proj = JSON.parse(fs.readFileSync(projPath, "utf8"));
const file = proj.files[0];
app.setState({ files: proj.files, selectedFileId: file.id, projectName: proj.projectName ?? file.name, standards: { ...app.getState().standards, ...(proj.standards ?? {}) } });
if (proj.ducts) ductStore.setState({ data: { ...ductStore.getState().data, ...proj.ducts } });
app.getState().setSolveMode(mode === "both" ? "both" : "aero");

const t0 = Date.now();
app.getState().solveActive();
// wait for the solve to finish (isSolving goes false and lastSolve is filled)
await new Promise((res, rej) => {
  const tick = () => { const s = app.getState(); if (!s.isSolving && s.lastSolve && Date.now() - t0 > 50) return res(); if (Date.now() - t0 > 30 * 60e3) return rej(new Error("timeout")); setTimeout(tick, 200); };
  setTimeout(tick, 200);
});
const s = app.getState(), d = ductStore.getState();
const ls = s.lastSolve ?? {};
const solved = { ...proj, files: s.files, ducts: d.data, ductResults: d.results ?? null,
  solveReport: { ok: ls.ok, iters: ls.iters, maxRes: ls.maxRes, issues: (ls.issues ?? []).slice(0, 500), logs: (ls.logs ?? []).slice(-80), status: s.status, mode, seconds: (Date.now() - t0) / 1000 } };
// Maps (duct analysis: per-duct flows, edges, densities) are written as plain objects, Sets as arrays; otherwise JSON drops them as {}
const replacer = (k, v) => (v instanceof Map ? Object.fromEntries(v) : v instanceof Set ? [...v] : v);
fs.writeFileSync(outPath, JSON.stringify(solved, replacer));
console.log(JSON.stringify({ ok: ls.ok, iters: ls.iters, maxRes: ls.maxRes, issues: (ls.issues ?? []).length, status: s.status, seconds: (Date.now() - t0) / 1000 }));
process.exit(0);
