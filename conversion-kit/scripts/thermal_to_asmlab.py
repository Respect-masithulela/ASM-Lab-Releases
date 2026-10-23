"""the source tool thermal inputs -> ASM Lab per-tunnel thermal fields, written into an ASM Lab project (full project .asmlab.json) in place.

Usage: py thermal_to_asmlab.py <project (full project).asmlab.json> <mine> <the source tool Input dir> <the source tool Output dir (full solve)>

  tunnels / shafts   thermal.rock {k, rho, c} from the mine's the source tool rock library (networks/rock_library.json, by Rock type),
                     thermal.wetness from the source tool's wetness rating (fraction of perimeter wet), thermal.ventilationTimeYr = the source tool Age
  ducts as tunnels   no rock heat (steel duct in air, not rock)
  Cooler: Fixed duty     thermal.cooler.dutyKw = the source tool input duty
  Cooler: Fixed outlet   thermal.cooler.targetDryBulb / targetWetBulb = the source tool input outlet DB / WB
  other point heat   (substations, hoists, pumps, equipment, auxiliary fans, fixed-flow devices, production zones, development headings):
                     thermal.electricKw = the air heat the source tool applied in its full solve (its duty ratings already applied), rock heat off
                     on that airway so it is not counted twice. ASM Lab adds it as dry (sensible) heat.
  fans               nothing: ASM Lab adds the fan's own heat from its operating point.
Site: rock properties and wetness = the mine's most common rock / wetness; rockHeatAll on.
"""
import collections, json, os, re, sys
import openpyxl

proj, mine, vin, vout = sys.argv[1:5]
HERE = os.path.dirname(os.path.abspath(__file__))
lib = json.load(open(os.path.join(HERE, "..", "data", "rock_library.json"), encoding="utf-8"))
WET = {k: v for k, v in lib["_wetness"].items() if not k.startswith("_")}
rocks = lib[mine]


def rows(p):
    if not os.path.exists(p): return []
    try: return list(openpyxl.load_workbook(p, read_only=True, data_only=True).active.iter_rows(values_only=True))
    except Exception: print("  unreadable:", p); return []


num = lambda s: float(re.findall(r"-?[\d.]+", str(s))[0])
geo = {}  # the source tool branch id -> (rock type, wetness, age)
for name, ri, wi, ai in (("tunnels", 7, 8, 5), ("shafts", 7, 8, 5)):
    for r in rows(os.path.join(vin, f"{name}.xlsx"))[1:]:
        if isinstance(r[0], (int, float)): geo[str(int(r[0]))] = (r[ri], r[wi], r[ai])
duct_ids = {str(int(r[0])) for r in rows(os.path.join(vin, "ducts.xlsx"))[1:] if isinstance(r[0], (int, float))}
cm_in = {str(int(r[0])): r for r in rows(os.path.join(vin, "control managers.xlsx"))[1:] if isinstance(r[0], (int, float))}
bo = rows(os.path.join(vout, "branches out.xlsx"))
heat = {}
if bo:
    h = [str(c).split("\n")[0].strip().lower() for c in bo[0]]; iH = h.index("air heat")
    for r in bo[1:]:
        if isinstance(r[0], (int, float)) and isinstance(r[iH], (int, float)) and isinstance(r[2], str): heat[str(int(r[0]))] = (r[2], float(r[iH]))
for r in rows(os.path.join(vout, "control managers out.xlsx"))[1:]:  # device heat where branches out lost the row
    if isinstance(r[0], (int, float)) and isinstance(r[9], (int, float)): heat.setdefault(str(int(r[0])), ("Control manager", float(r[9])))

j = json.load(open(proj, encoding="utf-8")); col = j["files"][0]
cnt, missing = collections.Counter(), collections.Counter()
rk_used, wet_used = collections.Counter(), collections.Counter()
for t in col["tunnels"]:
    tid = t["id"]; th = {}
    cm = cm_in.get(tid); det = str(cm[5]) if cm else ""; typ = str(cm[2]) if cm else ""
    if tid in geo and tid not in duct_ids:
        rt, wt, age = geo[tid]
        if rt in rocks: k, rho, c = rocks[rt]; th["rock"] = dict(k=k, rho=rho, c=c); rk_used[rt] += 1
        else: missing[f"rock '{rt}'"] += 1
        if wt in WET: th["wetness"] = WET[wt]; wet_used[wt] += 1
        elif re.match(r"Custom \[([\d.]+)%\]", str(wt)): th["wetness"] = float(re.match(r"Custom \[([\d.]+)%\]", str(wt))[1]) / 100; wet_used[wt] += 1  # the source tool custom wetness %
        if isinstance(age, (int, float)): th["ventilationTimeYr"] = max(float(age), 0.05)
        th["vrtEnabled"] = True; cnt["rock heat (the source tool rock, wetness, age)"] += 1
    elif tid in duct_ids:
        th["vrtEnabled"] = False; cnt["duct as tunnel: no rock heat"] += 1
    elif "Cooler: Fixed duty" in typ:
        th.update(vrtEnabled=False, cooler=dict(dutyKw=num(det.split("kW")[0]))); cnt["cooler fixed duty"] += 1
    elif "Cooler: Fixed outlet" in typ:
        # the source tool sets the outlet state whatever it takes (it heats too, and runs with the air reversed); ASM Lab's target cooler only
        # cools, so its duty switches on / off as the flow moves and the heat loop does not settle (Metal mine). Carried as the duty
        # the source tool applied: cooling -> cooler.dutyKw, heating -> point heat. the source tool's outlet targets are kept for reference.
        wb, db = re.findall(r"([\d.]+)/([\d.]+)", det)[0]
        q = heat.get(tid, ("", 0.0))[1]
        if os.environ.get("VB_BLIND") == "1":  # inputs only: the source tool's outlet targets
            th.update(vrtEnabled=False, cooler=dict(targetWetBulb=float(wb), targetDryBulb=float(db))); cnt["cooler fixed outlet -> the source tool targets (blind)"] += 1
        elif q < -0.5: th.update(vrtEnabled=False, cooler=dict(dutyKw=round(-q, 1), sourceTargetWetBulb=float(wb), sourceTargetDryBulb=float(db))); cnt["cooler fixed outlet -> the source tool applied duty"] += 1
        elif q > 0.5: th.update(vrtEnabled=False, electricKw=round(q, 1)); cnt["fixed outlet cooler heating in the source tool -> point heat"] += 1
        else: th["vrtEnabled"] = False; cnt["fixed outlet cooler idle in the source tool"] += 1
    elif t.get("device") == "fan":
        th["vrtEnabled"] = False; cnt["fan: ASM Lab fan heat"] += 1
    elif heat.get(tid, ("",))[0] == "Fan":
        # a the source tool fan held at a fixed flow ([FF] tier) is an ASM Lab fixed-flow regulator: ASM Lab adds its fan heat from the operating
        # point, as for a fan on a curve; the source tool's fan air heat as point heat as well counted it twice (Platinum [FF]: +3.1 MW)
        th["vrtEnabled"] = False; cnt["fixed-flow fan: ASM Lab fan heat (no point heat)"] += 1
    else:
        th["vrtEnabled"] = False
        q = heat.get(tid)
        # the source tool's branch air heat is m (h_out - h_in) with h_out the MIXED state at the outlet node, so passive devices (doors, reduced
        # areas, fixed pressure differences, fixed / measured flows, leakage) show the heat of mixing there (Platinum 856 after the BAC:
        # +1 011 kW, its bypass 806 -1 011 kW). Throttling adds no heat: only heat-making devices give point heat.
        if q and typ and not re.search(r"substation|heat|hoist|pump|equipment|machine|refrig|diesel|conveyor|crusher", typ, re.I):
            cnt[f"passive device ({typ}): the source tool mixing heat not carried"] += 1; q = None
        if q and q[1] > 0.5: th["electricKw"] = round(q[1], 1); cnt[f"point heat = the source tool air heat ({q[0].split('|')[-1].strip()})"] += 1
    t["thermal"] = th
site = col.setdefault("thermalSite", {})
if rk_used:
    k, rho, c = rocks[rk_used.most_common(1)[0][0]]; site.update(thermalConductivity=k, rockDensity=rho, specificHeat=c)
if wet_used: site["wetness"] = WET[wet_used.most_common(1)[0][0]]
site["rockHeatAll"] = True
site["_source"] = (site.get("_source", "").split(";")[0] + "; rock properties per airway from the source tool's rock library, wetness and age per airway from the source tool").lstrip("; ")
json.dump(j, open(proj, "w", encoding="utf-8"), indent=1)
print(f"{os.path.basename(proj)}: {dict(cnt)}; rocks {dict(rk_used)}; wetness {dict(wet_used)}; total point heat "
      f"{sum(t['thermal'].get('electricKw', 0) for t in col['tunnels']):.0f} kW" + (f"; MISSING {dict(missing)}" if missing else ""))
