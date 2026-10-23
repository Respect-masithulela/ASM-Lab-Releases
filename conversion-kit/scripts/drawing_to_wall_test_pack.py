"""Builds the 'use this.dxf' wall test files and solves them (aero) with the patched ASM Lab.
From the DXF (network embedded by ASM Lab): 109 nodes, 193 D-shaped 5 x 5 m tunnels, three fans (T67, T78, T89), nine brick walls (T113 ... T177), intake N109, exhausts N73, N85, N97.
Changes: fans on a fan curve (they were fixed 1000 Pa), nodes at z = 0, boundaries fixed at 86 kPa 26/18 C, k = 0.012; the nine walls are the only thing that differs between cases.
Usage: py build_pack.py <ASM assets dir> <asm_run.mjs>"""
import copy, csv, json, math, subprocess, sys
from pathlib import Path
assets, run = sys.argv[1:3]; H = Path(__file__).parent
X = json.load(open(H / "_extract.json"))["0"]; T0, N0 = X["tuns"], X["nodes"]
WALLS = ["T113", "T121", "T129", "T137", "T145", "T153", "T161", "T169", "T177"]
POS = {"P1": WALLS[:3], "P12": WALLS[:6], "P123": WALLS}          # walls 1-3, 1-6, all nine, counted along the diagonal
FANS = ["T67", "T78", "T89"]
FAN = [(0, 9150, 72), (188, 9150, 72), (282, 8950, 87), (377, 7730, 88), (471, 5050, 74), (565, 1150, 24), (590, 0, 1)]   # the source tool library "Main Fan", ref density 1.0   # Q m3/s, P Pa at 1.2 kg/m3, eta 75 %: a test curve sized to this network (the the source tool library fans are far too small for it)
CASES = {"C0_none": (None, None, [])}
for typ, wt, R in (("goodseal", "good-seal", 250), ("leakydoor", "louvre", 5)):   # R = the source tool presets (Ns2/m8)
    for pos, ids in POS.items(): CASES[f"{typ}_{pos}"] = (wt, R, ids)
x0 = min(v["xyz"][0] for v in N0.values()); y0 = min(v["xyz"][1] for v in N0.values())
def build(mode, cname, case):
    wt, R, ids = case; tag = f"{mode[0]}{list(CASES).index(cname)}"
    nodes = []
    for nid, v in N0.items():
        n = {"id": f"{nid}.{tag}", "x": v["xyz"][0] - x0, "y": v["xyz"][1] - y0, "z": 0, "kind": "junction", "temperature": 30.0, "wetBulbTemp": 20.0}
        if v["d"].get("bc") == "exhaust": n.update(bc="exhaust", fixedP=86000.0, kind="end")
        nodes.append(n)
    # intake portal: a 10 m stub from a surface node S0 to the manifold node N109 (so the surface connection is a dead-end branch, as the source tool needs)
    nodes.append({"id": f"S0.{tag}", "x": N0["N109"]["xyz"][0] - x0 - 10, "y": N0["N109"]["xyz"][1] - y0, "z": 0, "kind": "end", "temperature": 30.0, "wetBulbTemp": 20.0, "bc": "intake", "fixedP": 86000.0})
    tuns = []
    for tid, t in T0.items():
        o = {k: t[k] for k in ("width", "height", "length", "kind", "profile", "profileSource", "curveRadius", "arcSide") if k in t}
        fr, to = (t["to"], t["from"]) if tid in FANS else (t["from"], t["to"])   # exhaust fans: mine node -> surface node (the DXF has them the other way, blowing in)
        o.update(id=f"{tid}.{tag}", **{"from": f'{fr}.{tag}', "to": f'{to}.{tag}'}, layer=f'{tid} {t["layer"]}', k=0.012, kSource="user", shockLoss=0, airDensity=1.2, device="none")
        if tid in FANS:
            o.update(device="fan", fanKind="main", fan={"name": f"Fan {tid}", "operatingSpeedRps": 1, "position": 0.5}, speedRef=1, rhoRef=1.0, operatingSpeedRps=1,
                     fanCurve=[{"Q": q, "P": p, "eta": e} for q, p, e in FAN], **({"fanDensityScaling": False} if mode == "unscaled" else {}))
        if tid in ids: o.update(device="wall", wallType=wt, wallR=R)
        tuns.append(o)
    pt = {k: T0["T196"][k] for k in ("width", "height", "kind", "profile", "profileSource", "curveRadius", "arcSide")}
    tuns.append({**pt, "id": f"P0.{tag}", "from": f"S0.{tag}", "to": f"N109.{tag}", "length": 10.0, "layer": "P0 portal", "k": 0.012, "kSource": "user", "shockLoss": 0, "airDensity": 1.2, "device": "none"})
    name = f"{mode}_{cname}"
    f = {"id": f"usethis-{name}", "name": f"use this {name}", "origin": {"id": "N1", "x": nodes[0]["x"], "y": nodes[0]["y"], "z": 0, "kind": "junction"}, "nodes": nodes, "tunnels": tuns, "overlay": [],
         "treatAsTunnels": True, "showTunnels": True, "showOverlay": False, "tunnelColor": "#e8e8e8", "overlayColor": "#3b82f6", "overlayOpacity": 0.35,
         "stats": {"faces": 0, "polylines": 0, "tunnels": len(tuns), "nodes": len(nodes), "droppedOutliers": 0}, "source": "json", "junctions": [],
         "thermalSite": {"surfaceDryBulb": 30, "surfaceWetBulb": 20.0, "surfacePressure": 86.0}}
    return name, tag, {"files": [f], "ducts": None, "studioStrings": [], "studioSurfaces": [], "workingZ": 0, "standards": {"frictionDrive": 0.5, "frictionShaft": 0.5}, "projectName": f["name"]}
rows = []
for mode in ("scaled",):   # intake 30 / 20 C: what the source tool used (its node defaults), not the 26 / 18 of the global settings
    for cname, case in CASES.items():
        name, tag, p = build(mode, cname, case)
        src = H / "asm_files" / f"{name}.asmlab.json"; json.dump(p, open(src, "w"))
        out = H / "asm_results" / f"{name}_solved.asmlab.json"
        r = subprocess.run(["node", run, assets, str(src), "aero", str(out)], capture_output=True, text=True)
        if r.returncode: print(name, r.stderr[-300:]); continue
        s = json.load(open(out)); T = {t["id"][: -len(tag) - 1]: t for t in s["files"][0]["tunnels"]}; N = {n["id"][: -len(tag) - 1]: n for n in s["files"][0]["nodes"]}
        row = {"case": name, "status": s["solveReport"]["status"][:48]}
        for f_ in FANS:
            fo = T[f_].get("fanOp") or {}; row[f"{f_}_Q"] = fo.get("Q"); row[f"{f_}_P"] = fo.get("P")
        row["total_Q"] = sum(abs(T[f_].get("Q") or 0) for f_ in FANS)
        for w in WALLS: row[f"{w}_Q"] = T[w].get("Q"); row[f"{w}_dP"] = T[w].get("dP")
        for tid in list(T0) + ['P0']:
            if tid not in WALLS and tid not in FANS: row[f"{tid}_Q"] = T[tid].get("Q")
        for nid in list(N0) + ['S0']: row[f"{nid}_P"] = N[nid].get("P")
        rows.append(row)
def rnd(v): return round(v, 4) if isinstance(v, float) else v
with open(H / "asm_results" / "asm_summary.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); [w.writerow({k: rnd(v) for k, v in r.items()}) for r in rows]
for r in rows: print(f"{r['case']:<26} total {r['total_Q']:8.2f} m3/s | fans {r['T67_Q'] or 0:6.1f} {r['T78_Q'] or 0:6.1f} {r['T89_Q'] or 0:6.1f} @ {r['T67_P'] or 0:6.0f} Pa | wall T113 {r['T113_Q'] or 0:8.3f} T177 {r['T177_Q'] or 0:8.3f} | {r['status']}")
