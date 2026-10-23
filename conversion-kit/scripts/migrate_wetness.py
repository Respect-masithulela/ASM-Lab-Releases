"""Convert the wetness of a full project saved before the rating scale (ASM Lab 2026.1.19) to the rating scale.

Before: with the water-film model stated (thermalSite.wetWall == "film"), wetness was a tenth of the rating (Dry 0.01, Wet 0.055).
Now:    wetness is the rating (Very dry 0, Dry 0.1, Damp 0.275, Wet 0.55, Very wet 0.85); the film model uses a tenth of it inside.
ASM Lab does this itself on opening an old project. Use this script only for files you write or edit outside the app.

Usage: py migrate_wetness.py <in.asmlab.json> <out.asmlab.json>
Only files that state wetWall "film" are changed (site wetness and each airway's thermal.wetness, x10, at most 1).
A file with "wetnessScale": 2 is already on the rating scale and is left alone."""
import json, sys

src, out = sys.argv[1:3]
d = json.load(open(src, encoding="utf8"))
n = 0
if d.get("wetnessScale", 1) < 2:
    x10 = lambda v: min(1.0, round(v * 10, 6))
    for f in d.get("files", []):
        site = f.get("thermalSite") or {}
        if site.get("wetWall") != "film": continue
        if site.get("wetness") is not None: site["wetness"] = x10(site["wetness"]); n += 1
        for t in f.get("tunnels", []):
            th = t.get("thermal") or {}
            if th.get("wetness") is not None: th["wetness"] = x10(th["wetness"]); n += 1
    d["wetnessScale"] = 2
json.dump(d, open(out, "w", encoding="utf8"))
print(f"{n} wetness value(s) converted; wetnessScale = 2")
