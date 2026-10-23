# ASM Lab conversion kit

For people (and their AI models) who convert, build or edit ASM Lab projects outside the app. Read this first, then the scripts.

## What is here
| File | Does |
|---|---|
| `scripts/network_export_to_asmlab.py` | Another network tool's exported tables (branches, nodes, tunnels, shafts, fans, control managers) → an ASM Lab **network file** (`.asmlab.json`). The header comment lists every device rule. |
| `scripts/thermal_to_asmlab.py` | Adds heat inputs (rock, wetness, age, coolers, point heat) to a **full project**. |
| `scripts/ducts_to_asmlab.py` | Duct branches → ASM Lab ducts (`.ducts.json`). |
| `scripts/drawing_to_wall_test_pack.py`, `scripts/add_fans_and_walls.py` | Examples of building a full project in code: fan tables, wall devices, boundaries. |
| `scripts/run_headless.mjs` | Solves a full project with ASM Lab's own code, no window. `node run_headless.mjs <assets dir> <project> <aero|both> <out>` (assets dir = the folder holding `actions-*.js` and `store-*.js`). |
| `scripts/compare_with_reference.py` | Airway-by-airway comparison of wet bulb, speed and specific cooling power. Reports **min, max, median** and the spread. |
| `scripts/migrate_wetness.py` | Old film-model wetness → rating scale. |
| `scripts/psychro.py` | Moist-air density from pressure, dry and wet bulb. |
| `data/scp_table.json`, `data/rock_library.json` | SCP table (W/m², wet bulb × speed) and rock properties. |
| `example/` | `make_example.py` writes a small full project (fan table, wall, rock heat, bulk air cooler); `small_mine_solved.asmlab.json` is its solved result. |

## Two file shapes
1. **Network file** — `{projectName, notes, network:{nodes, airways, fans, regulators}, nodePositions, thermalSite?}`. Open it in ASM Lab (Open model file) and save it: that gives the full project.
2. **Full project** — `{wetnessScale, files:[{id,name,origin,nodes,tunnels,thermalSite,junctions,...}], ducts, studioStrings, studioSurfaces, workingZ, standards, projectName}`. Needed by the headless runner. See `example/make_example.py` for a complete minimal one.

Network nodes: `id, x, y, elevation, type (intake|exhaust), fixedPressure (Pa), temperature (dry bulb °C), wetBulbTemp (°C)`.
Airways: `id, fromNode, toNode, length (m), shape, width, height or diameter (m), frictionFactor (Atkinson k, kg/m³ basis 1.2), resistanceOverride (Ns²/m⁸), fixedQ (m³/s), device (none|fan|regulator), thermal{}`.
Full-project tunnels: `from, to, width, height, length, kind, profile, k, R, fixedQ, device (none|fan|regulator|wall), wallType, wallR, fanCurve [{Q m³/s, P Pa, eta %}], fanKind, rhoRef (kg/m³ the table was measured at), operatingSpeedRps, thermal{}`.
Units: metres, Pa, m³/s, kg/s, °C, kW. Elevation z is positive up; depth below the collar is negative z.

## Heat inputs (`thermal` on an airway, `thermalSite` on the collection)
- `vrtEnabled` rock heat on/off; `ventilationTimeYr` age; `rock {k W/m·°C, rho, c}`; `electricKw`, `heatKwPerM`, `heatLatent`; `dieselPower`; `explosiveKg` + `flushTime` (blasting heat; also marks a blast point for the re-entry time); `cooler {dutyKw | targetDryBulb/targetWetBulb | kind:"bac", waterInC, waterKgS, effectiveness}`.
- Site: `surfaceDryBulb, surfaceWetBulb, surfacePressure (kPa), wetWall ("film" default | "split"), wetness, rockHeatFactor (default 1.8), rockHeatAll`.
- **Wetness is a rating**: Very dry 0, Dry 0.1, Damp 0.275, Wet 0.55, Very wet 0.85 (or a custom 0–1). The film model uses a tenth of it internally. **Never type the tenth** (0.055 reads as nearly dry). Files saved before 2026.1.19 used the tenth for the film model; add `"wetnessScale": 2` to anything you write on the rating scale, or the app will multiply stated film values by 10 on opening.
- Fans add their own heat from the operating point, so do not also add the fan's air heat as point heat. Passive devices (doors, walls, fixed flows) add no heat.

## Rules learned the hard way
- A fan's direction is its airway direction: for an exhaust fan the airway runs mine node → surface node.
- Surface connections are dead-end nodes at the surface with `type` intake/exhaust and a fixed pressure; use one barometric pressure, corrected for elevation.
- Fixed mass flow (kg/s) → volume flow at the inlet node's air density (`psychro.py`).
- An irregular section: keep area and perimeter; use R = k·L·P/A³.
- Keep airway ids identical to the source's so results can be compared by id.
- Fan tables measured at another density: set `rhoRef`; ASM Lab scales with the density at the fan unless fan scaling is switched off.
- Report errors as min, max and median, not the median alone.

## Check your result
1. `node scripts/run_headless.mjs <assets> project.asmlab.json both solved.asmlab.json` — the printed line must say `"ok":true` and the status says whether it converged; read warnings in `solveReport.issues`.
2. Per airway, the solved file holds `Q, v, dP, rho` and `thermo.outlet {tdb, twb, ...}`.
3. Compare with another tool using `compare_with_reference.py`.
