"""Bord_and_Pillar_6Panel_brick_leak_0.12-0.50pct_seed350 -> ASM Lab project with real wall devices and fan curves.
 - the 225 'brick wall x.xx%' slot airways (width = leak share of the 6.5 m bord) become full-size 6.5 x 2.5 m airways with
   device wall, type Brick, and the resistance their slot had (k*P*L/A^3), so each keeps its own leak;
 - a fan on the return airway at each of the two exhaust nodes, with a fan table (flow, pressure, efficiency);
 - the boundary nodes held at 86 kPa; scaled to density (table at 1.0 kg/m3).
Usage: py build.py <source .asmlab.json> <out .asmlab.json> [fan: main|small]"""
import json, math, statistics as st, sys
src, out = sys.argv[1:3]; fantype = sys.argv[3] if len(sys.argv) > 3 else "main"
d = json.load(open(src)); net = d["network"]; pos = d["nodePositions"]
FANS = {"main": [(0, 9150, 72), (188, 9150, 72), (282, 8950, 87), (377, 7730, 88), (471, 5050, 74), (565, 1150, 24), (590, 0, 1)],   # the source tool library Main Fan, ref density 1.0
        "test": [(0, 2000, 75), (20, 1920, 75), (40, 1680, 75), (60, 1280, 75), (80, 720, 75), (100, 0, 75)]}   # the 6-point fan of the two-fan test model (ref density 1.2)
def rect(w, h):
    return {"kind": "rectangular", "span": w, "height": h, "archRatio": 1, "invertRise": 0, "pointCount": 4, "points": [{"x": -w/2, "y": 0}, {"x": w/2, "y": 0}, {"x": w/2, "y": h}, {"x": -w/2, "y": h}]}
nodes = []
for n in net["nodes"]:
    p = pos[n["id"]]; o = {"id": n["id"], "x": p["x"], "y": p["y"], "z": 0, "kind": "end" if n["type"] != "junction" else "junction", "temperature": 26.0, "wetBulbTemp": 18.0}
    if n["type"] != "junction": o.update(bc=n["type"], fixedP=86000.0)
    nodes.append(o)
exh = {n["id"] for n in net["nodes"] if n["type"] == "exhaust"}
tuns, walls, fans = [], [], []
for a in net["airways"]:
    w, h, L = a["width"], a["height"], a["length"]
    t = {"id": a["id"], "from": a["fromNode"], "to": a["toNode"], "length": L, "layer": a["name"], "kind": "drive", "profileSource": "imported", "curveRadius": 0, "arcSide": 1,
         "k": a["frictionFactor"], "kSource": "user", "shockLoss": a["shockLoss"], "airDensity": a["airDensity"], "device": "none"}
    if a["name"].startswith("brick wall"):
        A = w * h; P = 2 * (w + h); R = a["frictionFactor"] * P * L / A ** 3        # the slot's own Atkinson resistance at 1.0 kg/m3 basis
        t.update(width=6.5, height=2.5, profile=rect(6.5, 2.5), device="wall", wallType="brick", wallR=round(R, 1)); walls.append((a["name"], R))
    else:
        t.update(width=w, height=h, profile=rect(w, h))
    if a["toNode"] in exh:
        t.update(device="fan", fanKind="main", fan={"name": f"Fan {a['toNode']}", "operatingSpeedRps": 1, "position": 0.5}, speedRef=1, rhoRef=(1.2 if fantype == "test" else 1.0), operatingSpeedRps=1,
                 fanCurve=[{"Q": q, "P": p, "eta": e} for q, p, e in FANS[fantype]]); fans.append(a["name"])
    tuns.append(t)
Rs = [r for _, r in walls]; print("walls", len(walls), "R min/median/max", round(min(Rs)), round(st.median(Rs)), round(max(Rs)), "| fans on", fans)
f = {"id": "bordpillar-seed350", "name": d["projectName"], "origin": {"id": nodes[0]["id"], "x": nodes[0]["x"], "y": nodes[0]["y"], "z": 0, "kind": "junction"}, "nodes": nodes, "tunnels": tuns, "overlay": [],
     "treatAsTunnels": True, "showTunnels": True, "showOverlay": False, "tunnelColor": "#6b8cbe", "overlayColor": "#3b82f6", "overlayOpacity": 0.35,
     "stats": {"faces": 0, "polylines": len(tuns), "tunnels": len(tuns), "nodes": len(nodes), "droppedOutliers": 0}, "source": "json", "junctions": [],
     "thermalSite": {"surfaceDryBulb": 26, "surfaceWetBulb": 18.0, "surfacePressure": 86.0}}
json.dump({"files": [f], "ducts": None, "studioStrings": [], "studioSurfaces": [], "workingZ": 0, "standards": {"frictionDrive": 0.5, "frictionShaft": 0.5}, "projectName": d["projectName"]}, open(out, "w"))
