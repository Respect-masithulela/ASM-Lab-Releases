"""Writes small_mine.asmlab.json: a full ASM Lab project with 6 nodes, 5 airways, one fan on a table, one wall, rock heat and a cooler.
Run: py make_example.py   then   node ../scripts/run_headless.mjs <assets> small_mine.asmlab.json both small_mine_solved.asmlab.json"""
import json

def rect(w, h):
    return {"kind": "rectangular", "span": w, "height": h, "archRatio": 1, "invertRise": 0, "pointCount": 4,
            "points": [{"x": -w / 2, "y": 0}, {"x": w / 2, "y": 0}, {"x": w / 2, "y": h}, {"x": -w / 2, "y": h}]}

#        id    x     y    z (m, z is elevation)   boundary
N = [("S", 0, 0, 0, "intake"), ("A", 0, 400, -300, None), ("B", 300, 400, -300, None), ("C", 300, 0, 0, None), ("X", 600, 0, 0, "exhaust")]
nodes = []
for i, x, y, z, bc in N:
    n = {"id": i, "x": x, "y": y, "z": z, "kind": "end" if bc else "junction", "temperature": 28.0, "wetBulbTemp": 20.0}
    if bc: n.update(bc=bc, fixedP=101325.0)
    nodes.append(n)

def airway(tid, a, b, w=5, h=5, **extra):
    pa = next(n for n in nodes if n["id"] == a); pb = next(n for n in nodes if n["id"] == b)
    L = round(((pa["x"] - pb["x"]) ** 2 + (pa["y"] - pb["y"]) ** 2 + (pa["z"] - pb["z"]) ** 2) ** 0.5, 1)
    t = {"id": tid, "from": a, "to": b, "width": w, "height": h, "length": L, "layer": tid, "kind": "drive", "profile": rect(w, h),
         "profileSource": "imported", "curveRadius": 0, "arcSide": 1, "k": 0.012, "kSource": "user", "shockLoss": 0, "airDensity": 1.2, "device": "none"}
    t.update(extra); return t

tuns = [
    airway("shaft_down", "S", "A", 6, 6, kind="shaft", thermal={"vrtEnabled": True, "ventilationTimeYr": 5, "wetness": 0.1}),   # wetness 0.1 = rating "Dry"
    airway("level", "A", "B", thermal={"vrtEnabled": True, "ventilationTimeYr": 3, "wetness": 0.275, "electricKw": 150}),     # "Damp"; 150 kW of machines
    airway("wall_on_level", "B", "C", device="wall", wallType="brick", wallR=1000, thermal={"vrtEnabled": False}),
    airway("shaft_up", "B", "C", 6, 6, kind="shaft", thermal={"vrtEnabled": True, "ventilationTimeYr": 5, "wetness": 0.1, "cooler": {"kind": "bac", "dutyKw": 800}}),
    airway("fan_drift", "C", "X", device="fan", fanKind="main", speedRef=1, rhoRef=1.2, operatingSpeedRps=1, fan={"name": "Main fan", "operatingSpeedRps": 1, "position": 0.5},
           fanCurve=[{"Q": q, "P": p, "eta": e} for q, p, e in [(0, 3000, 70), (100, 2800, 78), (200, 2200, 82), (300, 1200, 70), (350, 0, 20)]]),
]
f = {"id": "small", "name": "small mine", "origin": {"id": "S", "x": 0, "y": 0, "z": 0, "kind": "end"}, "nodes": nodes, "tunnels": tuns, "overlay": [], "treatAsTunnels": True,
     "showTunnels": True, "showOverlay": False, "tunnelColor": "#6b8cbe", "overlayColor": "#3b82f6", "overlayOpacity": 0.35,
     "stats": {"faces": 0, "polylines": len(tuns), "tunnels": len(tuns), "nodes": len(nodes), "droppedOutliers": 0}, "source": "json", "junctions": [],
     "thermalSite": {"surfaceDryBulb": 28, "surfaceWetBulb": 20, "surfacePressure": 101.325, "wetWall": "film", "wetness": 0.1, "rockHeatAll": True}}
json.dump({"wetnessScale": 2, "files": [f], "ducts": None, "studioStrings": [], "studioSurfaces": [], "workingZ": 0,
           "standards": {"frictionDrive": 0.012, "frictionShaft": 0.012}, "projectName": "small mine"}, open("small_mine.asmlab.json", "w"), indent=1)
print("wrote small_mine.asmlab.json")
