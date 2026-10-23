"""Compare an ASM Lab solve with another network tool's results, airway by airway: outlet wet bulb, air speed, and the specific
cooling power (SCP) the table gives for each. Report the error as min, max and median (and the spread), not the median alone.

Usage: py compare_with_reference.py <reference tunnels table .xlsx> <solved ASM Lab project .asmlab.json> [pairs_out.json]

Reference table columns (header text starts with): ID, Velocity, "Wet bulb (outlet", "Dry bulb (outlet".
ASM Lab file: a full project solved with heat (see run_headless.mjs, mode "both"), airway ids equal to the reference ids.
Airways are compared only inside the SCP table (speed 0.1-4.5 m/s, wet bulb 20-34.9 C), taken at the reference's own values."""
import json, os, statistics as st, sys
import openpyxl

ref_xlsx, solved = sys.argv[1], sys.argv[2]
pairs_out = sys.argv[3] if len(sys.argv) > 3 else None
T = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "scp_table.json")))
vel, wbs, S = T["velocity"], T["wet_bulb"], T["scp"]


def bracket(xs, x):
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x: lo = mid
        else: hi = mid
    return lo, hi, (x - xs[lo]) / (xs[hi] - xs[lo])


def scp(wb, v):
    wb = min(max(wb, wbs[0]), wbs[-1]); v = min(max(abs(v), vel[0]), vel[-1])
    a = bracket(wbs, wb); b = bracket(vel, v)
    top = S[a[0]][b[0]] * (1 - b[2]) + S[a[0]][b[1]] * b[2]
    bot = S[a[1]][b[0]] * (1 - b[2]) + S[a[1]][b[1]] * b[2]
    return top * (1 - a[2]) + bot * a[2]


rows = list(openpyxl.load_workbook(ref_xlsx, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))
hdr = [str(x) for x in rows[0]]
col = lambda p: [i for i, x in enumerate(hdr) if x.startswith(p)][0]
iid, iv, iwo = col("ID"), col("Velocity"), col("Wet bulb (outlet")
V = {}
for r in rows[1:]:
    try: V[str(int(r[iid]))] = (abs(float(r[iv])), float(r[iwo]))
    except Exception: pass
s = json.load(open(solved, encoding="utf8"))
tun = {}
for f in s["files"]:
    for t in f["tunnels"]:
        th = t.get("thermo")
        if th and t.get("v") is not None: tun[str(t["id"])] = (abs(t["v"]), th["outlet"]["twb"])
pairs = [(k, vv, tun[k][0], wv, tun[k][1], scp(wv, vv), scp(tun[k][1], tun[k][0])) for k, (vv, wv) in V.items() if k in tun]
inr = [p for p in pairs if 0.1 <= p[1] <= 4.5 and 20 <= p[3] <= 34.9]
print(f"{len(V)} reference airways, {len(tun)} ASM Lab airways with heat results, {len(pairs)} matched by id, {len(inr)} inside the SCP table")


def stat(name, xs):
    xs = sorted(xs); a = sorted(abs(x) for x in xs)
    print(f"  {name}: min {xs[0]:+.2f}  max {xs[-1]:+.2f}  median {st.median(xs):+.3f}  |  |error| median {st.median(a):.3f}  p90 {a[int(.9 * len(a))]:.3f}  max {a[-1]:.2f}")


stat("speed, ASM Lab - reference (m/s)", [p[2] - p[1] for p in inr])
stat("outlet wet bulb, ASM Lab - reference (C)", [p[4] - p[3] for p in inr])
stat("SCP from each side's own wet bulb and speed (W/m2)", [p[6] - p[5] for p in inr])
same = sum(1 for p in inr if (p[5] < 300) == (p[6] < 300)) / len(inr) * 100
print(f"  same side of the 300 W/m2 design minimum in {same:.0f} % of airways")
if pairs_out:
    json.dump([dict(id=p[0], v_ref=p[1], v_asm=p[2], wb_ref=p[3], wb_asm=p[4], scp_ref=p[5], scp_asm=p[6]) for p in pairs], open(pairs_out, "w"))
