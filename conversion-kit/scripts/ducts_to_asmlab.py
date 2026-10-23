"""Turn the source tool duct systems (duct branches + fixed-flow 'fans' + in-line devices + leakage branches) into ASM Lab ducts (.ducts.json).

Usage: py ducts_to_asmlab.py <project.asmlab.json> <the source tool branches.xlsx> <the source tool Ducts.xlsx> <the source tool control managers.xlsx> [<the source tool ducts out.xlsx>]
Rewrites the project (duct, duct-fan, in-line device and leak branches removed) and writes <project>.ducts.json next to it.

Any duct topology is carried, including Y-pieces, manifolds and loops, the way ASM Lab stores them: a duct system is split at its
key nodes (open ends, junctions, and points where the duct meets the network) into segments; every segment is one ASM duct running
from one duct node to another, and ducts that share a duct node are joined there (as in ASM's own Y-branch files).
  ends   = a duct end on a network node is open to the tunnel: each segment ending there has its own duct node (two fans in parallel
           drawing from one tunnel node are two open inlets, not a closed elbow)
  hosts  = a key node that is still a network node hosts its duct node directly; one that was only a the source tool duct node is placed as an
           ASM virtual node (vnode) on the nearest airway, at the projected position
  route  = shortest airway path between the two hosts (vnode -> airway end -> ... -> vnode)
  dir.   = the segment runs in the source tool's flow direction (ducts out), else in the fixed-flow direction, else as drawn
  fan    = the source tool fixed flow Q, near-vertical curve: 30 kPa at 0.995 Q, 0 Pa at 1.005 Q, at its chainage along the segment;
           a second fan in series on a segment without leakage gets the source tool's pressure rise (fans out.xlsx) as a flat curve
  leak   = the source tool '(Leakage)Fixed resistance' branches on the segment: section = L/(n+1), Lc = 1000 sqrt(1000) / (section sqrt(R mean))
  k      = with ducts out, set so the segment (route length, 1.2 kg/m3) has the source tool's resistance corrected from in-situ density to 1.2
"""
import sys, os, json, re, math, heapq, collections
import openpyxl

proj, fbr, fdu, fcm = sys.argv[1:5]
fout = sys.argv[5] if len(sys.argv) > 5 else None
L = lambda f: list(openpyxl.load_workbook(f, read_only=True, data_only=True).active.iter_rows(values_only=True))[1:]
num = lambda s: float(re.findall(r"-?[\d.]+", str(s))[0])
# VB_BLIND=1: the source tool inputs only (no direction, k correction, series-fan pressure or kg/s conversion from the source tool's solution)
BLIND = os.environ.get("VB_BLIND") == "1"
dout = {r[0]: r for r in L(fout)} if fout and not BLIND else {}
_fo = os.path.join(os.path.dirname(fout), "fans out.xlsx") if fout else ""
fanP = {r[0]: abs(float(r[6])) for r in L(_fo)} if _fo and os.path.exists(_fo) and not BLIND else {}
# VB_FANS=fixed: fixed-flow test, every running duct fan is a fixed flow at the volume the source tool's solution gives it
FIXED_FANS = os.environ.get("VB_FANS") == "fixed"
fanQ = {r[0]: float(r[4]) for r in L(_fo) if isinstance(r[4], (int, float))} if _fo and os.path.exists(_fo) else {}
br = {r[0]: r for r in L(fbr)}; du = {r[0]: r for r in L(fdu)}; cm = {r[0]: r for r in L(fcm)}
j = json.load(open(proj)); net = j["network"]
P = {n["id"]: (n["x"], n["y"], n["elevation"]) for n in net["nodes"]}
nb = collections.defaultdict(list)
for r in br.values(): nb[r[5]].append(r[0]); nb[r[6]].append(r[0])
dnodes = {n for d in du for n in (br[d][5], br[d][6])}
isff = lambda b: "Fixed flow" in str(br[b][2])
isleak = lambda b: "(Leakage)Fixed resistance" in str(br[b][2]) or "(Leakage)Percentage flow" in str(br[b][2])
isfan = lambda b: str(br[b][2]) == "Fan"  # library-curve fan (curve already in the project's fan list, from vuma2asm)
pfan = {f["airwayId"]: f for f in json.load(open(proj))["network"]["fans"]}
member = set(du) | {b for b in br if (isff(b) or isfan(b)) and (br[b][5] in dnodes or br[b][6] in dnodes)}
inline = {b for b in br if b not in member and str(br[b][2]).startswith("Control manager") and not isleak(b)
          and all(len(nb[n]) == 2 and any(y in member for y in nb[n] if y != b) for n in (br[b][5], br[b][6]))}
member |= inline
# devices that belong to the duct by name (the source tool models drawn without a duct table: 'DUCT' splitters / regulators inside the duct,
# 'Duct leakage' fixed-pressure links that join the duct ends to the tunnels) are part of the duct system, except true leakage branches
named = {b for b in br if b not in member and str(br[b][2]).startswith("Control manager") and not isleak(b)
         and ("duct" in str(br[b][1]).lower() or "duct" in str(br[b][2]).lower())  # by name, or by type ('Duct through wall')
         and (br[b][5] in dnodes or br[b][6] in dnodes or any(y in member for n in (br[b][5], br[b][6]) for y in nb[n]))}
member |= named; inline |= named
_cmr = os.path.join(os.path.dirname(fcm), "CM results.xlsx")
if not os.path.exists(_cmr) and fout: _cmr = os.path.join(os.path.dirname(fout), "control managers out.xlsx")
cmR = {r[0]: abs(float(r[8])) for r in L(_cmr) if len(r) > 8 and isinstance(r[8], (int, float))} if os.path.exists(_cmr) else {}
cmQ = {r[0]: abs(float(r[4])) for r in L(_cmr) if len(r) > 4 and isinstance(r[4], (int, float))} if os.path.exists(_cmr) else {}
# the source tool fixed flows are given in m3/s or kg/s; a mass flow becomes the volume flow the source tool ran it at (M / rho of its own solution)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psychro import rho as _rho
_nin = {r[1]: r for r in L(os.path.join(os.path.dirname(fbr), "nodes.xlsx"))} if os.path.exists(os.path.join(os.path.dirname(fbr), "nodes.xlsx")) else {}
def ffq(b):
    m = num(cm[b][5])
    if "kg/s" not in str(cm[b][5]): return m
    n = _nin.get(br[b][5])
    if BLIND and n: return m / _rho(float(n[9]), float(n[8]), float(n[7]))
    return cmQ.get(b) or m / 1.2
leaks_at = collections.defaultdict(list)
for b in br:
    if isleak(b):
        for n in (br[b][5], br[b][6]):
            if n in dnodes: leaks_at[n].append(b)
seen, systems = set(), []
for d in du:
    if d in seen: continue
    st, c = [d], set()
    while st:
        x = st.pop()
        if x in c: continue
        c.add(x)
        for n in (br[x][5], br[x][6]):
            st += [y for y in nb[n] if y in member and y not in c]
    seen |= c; systems.append(c)

drop = {str(b) for s in systems for b in s} | {str(b) for n in leaks_at for b in leaks_at[n]}
rest = [a for a in net["airways"] if a["id"] not in drop]
rest_nodes = {a["fromNode"] for a in rest} | {a["toNode"] for a in rest}
G = collections.defaultdict(list)
for a in rest: G[a["fromNode"]].append((a["toNode"], a["length"])); G[a["toNode"]].append((a["fromNode"], a["length"]))
dist3 = lambda p, q: math.dist(p, q)
vnodes, vpos, notes = [], {}, collections.Counter()


def host(n):
    """network node id, or a vnode on the nearest remaining airway"""
    if n in rest_nodes: return f"SAMPLE|{n}"
    if ("v", n) in vpos: return vpos[("v", n)]
    p, best = P[n], None
    for a in rest:
        A_, B_ = P[a["fromNode"]], P[a["toNode"]]; ab = [B_[i] - A_[i] for i in range(3)]; l2 = sum(x * x for x in ab) or 1e-9
        t = max(0.02, min(0.98, sum((p[i] - A_[i]) * ab[i] for i in range(3)) / l2))
        dd = dist3(p, [A_[i] + t * ab[i] for i in range(3)])
        if best is None or dd < best[0]: best = (dd, a, t)
    _, a, t = best
    vid = f"V{len(vnodes) + 1}"; vnodes.append({"id": vid, "a": f"SAMPLE|{a['fromNode']}", "b": f"SAMPLE|{a['toNode']}", "t": round(t, 6)})
    vpos[("v", n)] = vid; vpos[vid] = (a, t); notes["duct nodes placed as vnodes on the nearest airway"] += 1
    return vid


def ends(h):
    """(network node, cost) entry points of a host"""
    if h.startswith("SAMPLE|"): return [(h[7:], 0.0)]
    a, t = vpos[h]; return [(a["fromNode"], t * a["length"]), (a["toNode"], (1 - t) * a["length"])]


def route(h1, h2):
    if h1 == h2: return None
    if not h1.startswith("SAMPLE|") and not h2.startswith("SAMPLE|") and vpos[h1][0] is vpos[h2][0]: return [h1, h2]
    src, dst = dict(ends(h1)), dict(ends(h2))
    dist, back, hq = dict(src), {}, [(c, n) for n, c in src.items()]
    heapq.heapify(hq); best = (1e18, None)
    while hq:
        dd, u = heapq.heappop(hq)
        if dd > dist.get(u, 1e18) or dd >= best[0]: continue
        if u in dst and dd + dst[u] < best[0]: best = (dd + dst[u], u)
        for v, w in G[u]:
            if dd + w < dist.get(v, 1e18): dist[v] = dd + w; back[v] = u; heapq.heappush(hq, (dd + w, v))
    if best[1] is None: return None
    path = [best[1]]
    while path[-1] not in src: path.append(back[path[-1]])
    r = ([] if h1.startswith("SAMPLE|") else [h1]) + [f"SAMPLE|{n}" for n in path[::-1]] + ([] if h2.startswith("SAMPLE|") else [h2])
    return [x for i, x in enumerate(r) if i == 0 or x != r[i - 1]]


def xyz(h):
    if h.startswith("SAMPLE|"): return P[h[7:]]
    a, t = vpos[h]; A_, B_ = P[a["fromNode"]], P[a["toNode"]]; return [A_[i] + t * (B_[i] - A_[i]) for i in range(3)]


blen = lambda b: float(du[b][2]) if b in du else 0.5
ducts, dnode_of, k, leak_done = [], {}, 0, set(); LEFT = []
for si, c in enumerate(systems, 1):
    deg = collections.Counter(n for x in c for n in (br[x][5], br[x][6]))
    key = {n for n in deg if deg[n] != 2 or any(y not in c and not isleak(y) for y in nb[n])}
    if not key: key = {br[next(iter(c))][5]}  # closed duct loop with no outside connection: cut it anywhere
    used = set()
    for a0 in sorted(key):
        for b0 in [x for x in c if a0 in (br[x][5], br[x][6])]:
            if b0 in used: continue
            seg, start_of, cur, ch, fans, leaks, b = [], {}, a0, 0.0, [], [], b0
            while True:
                used.add(b); seg.append(b); start_of[b] = cur
                if isff(b): fans.append((ch, ffq(b) if b in cm else None, b, br[b][5] == cur))
                elif isfan(b) and FIXED_FANS and fanQ.get(b, 0) > 0.05: fans.append((ch, fanQ[b], b, br[b][5] == cur))  # fixed-flow test
                elif isfan(b): fans.append((ch, "curve", b, br[b][5] == cur))
                cur = br[b][6] if br[b][5] == cur else br[b][5]; ch += blen(b)
                if cur in key: break
                leaks += [(ch, y) for y in leaks_at.get(cur, [])]
                b = next((x for x in c if x not in used and cur in (br[x][5], br[x][6])), None)
                if b is None: break
            n1, n2, Lseg = a0, cur, ch
            for endn, pos in ((a0, 0.0), (cur, ch)):  # leaks at a junction / end of the duct go to the first segment that reaches it
                for y in leaks_at.get(endn, []):
                    if y not in leak_done: leaks.append((pos, y))
            leak_done.update(y for _, y in leaks)
            # direction: the source tool flow on a duct branch of the segment (sign is relative to the branch's node in -> node out)
            fwd = next(((start_of[x] == br[x][5]) == (float(dout[x][3]) > 0) for x in seg if x in dout and dout[x][3]), None)
            if fwd is None and fans: fwd = fans[0][3]
            if fwd is False:
                n1, n2 = n2, n1
                fans = [(Lseg - p, q, fb, not d_) for p, q, fb, d_ in fans][::-1]; leaks = [(Lseg - p, y) for p, y in leaks][::-1]
            dsz = next((x for x in seg if x in du), None)
            stub = dsz is None and bool(fans)
            if stub:  # a fan alone between a tunnel and a duct junction: a short duct of the system's size carrying the fan
                dsz = next(x for x in c if x in du); notes["fan-only duct stubs written as short ducts"] += 1
            if dsz is None: notes["segments without a duct branch (left out)"] += 1; LEFT.append((seg, fans)); continue
            h1, h2 = host(n1), host(n2)
            r = route(h1, h2)
            if r is None: notes["segments with no route between their ends (left out)"] += 1; continue
            k += 1; did = f"D{k}"
            D = float(re.findall(r"[\d.]+", du[dsz][3])[0]); kf = num(du[dsz][4])
            Lr = sum(dist3(xyz(a), xyz(b)) for a, b in zip(r, r[1:]))
            Rv = sum(abs(dout[x][7]) * 1.2 / (abs(dout[x][4]) / abs(dout[x][3])) for x in seg if x in dout and dout[x][3] and dout[x][7])
            Rv += sum(cmR.get(x, 0.0) for x in seg if x in named) if not BLIND else 0.0  # resistance of in-duct devices (splitters, end fittings)
            if Rv > 0 and Lr > 0: kf = round(kf * Rv / (kf * Lr * math.pi * D / (math.pi * D * D / 4) ** 3), 6)
            elif stub:
                # the source tool's fan / fixed-flow device has no friction, but the stub is routed along the tunnels between its ends (Platinum 972:
                # 733 m for 41 m, 54 m/s): with duct k it needed 30 kPa and 1.15 MW of fan heat. No friction, as the the source tool device.
                kf = 1e-6; notes["fan-only stubs: no duct friction (the source tool device has none)"] += 1
            # fixed-resistance leaks: their R; percentage-flow leaks: R = dP / Q^2 that the source tool solved for them (negligible leak if ~no flow)
            leakR = [num(cm[y][5]) if "Fixed resistance" in str(br[y][2]) else cmR[y] for _, y in leaks if y in cm and ("Fixed resistance" in str(br[y][2]) or (cmR.get(y) and not BLIND))]
            n_leak = len(leaks); sec = Lseg / (n_leak + 1) if n_leak else 20.0
            Lc = (1000 * math.sqrt(1000) / (sec * math.sqrt(sum(leakR) / len(leakR)))) if leakR else 0.0
            fo = []
            for (pos, q, fb, along) in fans:
                if q is None: continue
                raw = round(min(max(pos * Lr / Lseg if Lseg else pos, 1.0), max(Lr - 1.0, 1.0)), 2)
                if q == "curve":
                    pf = pfan.get(str(fb))
                    if not pf or not pf["points"]: notes["duct curve fans without a curve (left out)"] += 1; continue
                    if not along: notes["duct curve fans pointing against the duct flow (kept in the duct direction)"] += 1
                    fo.append({"id": f"{did}F{len(fo) + 1}", "raw": raw, "fanKind": "auxiliary", "fanSource": "points",
                               "fan": {"name": pf["name"], "source": "points", "controlMode": "curve" if pf.get("operatingSpeedRps", 1) else "off",
                                       "points": pf["points"], "rhoRef": pf.get("rhoRef", 1.2)}})
                    notes["duct curve fans (the source tool fan library)"] += 1; continue
                if fo and not n_leak and fb in fanP:
                    fo.append({"id": f"{did}F{len(fo) + 1}", "raw": raw, "fanKind": "auxiliary", "fanSource": "points",
                               "fan": {"name": f"the source tool fan {fb} in series, {fanP[fb]:g} Pa (the source tool pressure rise)", "source": "points", "controlMode": "curve",
                                       "points": [{"Q": 0, "P": fanP[fb]}, {"Q": round(3 * q, 4), "P": fanP[fb]}], "rhoRef": 1.2}})
                    notes["series duct fan as fixed the source tool pressure rise"] += 1; continue
                fo.append({"id": f"{did}F{len(fo) + 1}", "raw": raw, "fanKind": "auxiliary", "fanSource": "points",
                           "fan": {"name": f"the source tool fixed flow {q:g} m3/s (branch {fb})", "source": "points", "controlMode": "curve",
                                   "points": [{"Q": 0, "P": 30000}, {"Q": round(0.995 * q, 6), "P": 30000}, {"Q": round(1.005 * q, 6), "P": 0}], "rhoRef": 1.2}})
            # a duct end on a network node is an open end (it exchanges air with the tunnel), so every segment gets its own end there;
            # only junctions inside the duct system (the source tool duct nodes, placed as vnodes) are shared, closed joints
            ids = []
            for n, h in ((n1, h1), (n2, h2)):
                kk = n if n not in rest_nodes else (n, did, len(ids))
                if kk not in dnode_of: dnode_of[kk] = (f"DN{len(dnode_of) + 1}", h)
                ids.append(dnode_of[kk][0])
            ducts.append({"id": did, "name": f"Duct {k} (system {si}; the source tool branches {', '.join(map(str, seg))})", "route": r,
                          "D_mm": round(D * 1000), "k": kf, "kb": kf, "side": "left", "vert": "roof", "pipeLen": 3, "kIn": 0, "kOut": 0,
                          "from": ids[0], "to": ids[1], "pointPins": {}, "legOffsets": {}, "reducers": [],
                          "leak": {"on": bool(n_leak), "Lc": round(Lc, 3), "section": round(sec, 2)}, "fans": fo})
            notes["duct segments written"] += 1; notes["duct leak branches folded into duct leakage"] += n_leak
            notes["in-line devices absorbed into ducts (their small R dropped)"] += len(set(seg) & inline)
    notes["the source tool duct systems"] += 1
    if any(deg[n] >= 3 for n in key): notes["duct systems with junctions (Y-pieces / manifolds)"] += 1

net["airways"] = rest
net["regulators"] = [r for r in net["regulators"] if r["airwayId"] not in drop]
net["fans"] = [f for f in net["fans"] if f["airwayId"] not in drop]
net["nodes"] = [n for n in net["nodes"] if n["id"] in rest_nodes]
j["nodePositions"] = {kk: v for kk, v in j["nodePositions"].items() if kk in rest_nodes}
j["notes"] = f"Ducts: {notes['the source tool duct systems']} the source tool duct systems as {len(ducts)} ASM duct segments joined at shared duct nodes (see .ducts.json). " + j["notes"]
json.dump(j, open(proj, "w"), indent=1)
dn = [{"id": i, "host": h, "p": None} for i, h in dnode_of.values()]
json.dump({"format": "asmlab-ducts", "version": 1, "data": {"vnodes": vnodes, "ducts": ducts, "ductNodes": dn, "machines": [], "assets": [],
           "seq": {"d": len(ducts), "c": 0, "dn": len(dn), "v": len(vnodes), "m": 0, "a": 0}}}, open(proj.replace(".asmlab.json", ".ducts.json"), "w"), indent=1)
left = [a["id"] for a in rest if "[Duct]" in a["name"]]
print(dict(notes)); print(len(net["nodes"]), "nodes,", len(rest), "airways left;", len(left), "duct airways left in the network")
