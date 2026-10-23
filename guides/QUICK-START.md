# ASM Lab quick start

Follow the sections in order for a first model. Units: metres, Pa, m³/s, kW, °C. Every button is listed under **Help**.

## 1. Start
Choose *New model* and name it, or *Open model file* for a saved project, or *Import* for a DXF or spreadsheet. The status bar at the bottom says what each tool wants next.

## 2. Drawing tunnels and naming them
1. **Home → Draw tunnel** (or key **A**). Click the start, then each next point; **Esc** ends the chain. Each click makes a node; a tunnel joins two nodes.
2. Set the section **before** drawing in the Properties panel: Width and Height, or one **Diameter** if the pen's section is Circular. The pen and these fields always show the same size.
3. **Working Z** is the level you draw on. Use the up/down arrows beside the view to change level.
4. **Curved tunnel**, **Add shaft** and the Design tab tools (decline, ramp, level loop…) draw other shapes from the same panel.
5. **Naming.** Select an airway: *Name* in the Properties panel renames it (its id, such as T12, stays the same). Select a collection in the Outliner to rename that. Two collections may not share a name: the app asks you to rename one.
6. **Edit.** *Add node* cuts an airway where you click. *Merge nodes* joins two nodes. *Fillet* rounds a corner between two airways (starts at R = 10 m, change it in Properties). *Extend* carries an airway on until it meets another. *Delete* removes what you click.

## 3. Geometry
- **Section:** Width, Height (m), or the pen's cross-section (rectangle, D-shape, arch, circle, or a drawn outline). The solver uses the section's area and perimeter.
- **Curve R** and **Arc side** make an airway an arc; *Flip curve direction* swaps the side.
- **Length** comes from the node positions; the shaft depth comes from the nodes' elevations.
- Boundaries: set a node's **Boundary** to intake or exhaust and give the surface air in the Thermal panel (dry bulb, wet bulb, pressure).

## 4. Resistance
- **k** is the friction factor (kg/m³ basis, about 0.01 for a drive). The airway's resistance is R = k · L · P / A³ (Ns²/m⁸).
- Defaults for drives and shafts are in Settings. Give an airway its own **k** to override them.
- To fix an airway's resistance outright, type **R**. It replaces k.
- Shock losses at bends and junctions are added from the shock loss factor on the airway.

## 5. Devices
Select an airway, then set its **Device** or use the Create group: *Place fan*, *Add regulator*, *Add wall*, *Add cooler*. An airway holds one device.

## 6. Fans and fan curves
1. **Home → Place fan** (Main, Booster or Auxiliary), click the airway, then click the direction the fan blows. The fan sits in that airway.
2. Open **Fan curves** (Simulate group) to see and edit the curve. Choose how it is defined:
   - **Library**: a catalogue fan.
   - **Quadratic**: shut-off pressure P₀, a duty point (Q, P), speed and density.
   - **Field test**: rows of Q, P (and W) with the density measured and the density at deployment.
   - **Table** (imported or pasted): rows of Q, P, power W and efficiency η. Add a row with *Add row*.
3. **State the density the table was measured at (ρref).** The box *Correct the curve for air density* scales the table by the air density at the fan; switch it off to use the table exactly as entered at any density.
4. A fan can be switched off with its damper shut or open. If you swap to another source and want the table back, use *Use the imported table again*.
5. Solve, then read the fan's operating point (Q, P, power) in its Properties. A warning appears if it is stalled, reversed or beyond the curve.

## 7. Walls
1. **Home → Add wall**: the arrow lists the types (brick, concrete, shotcrete, good seal, poor seal, brattice, louvre, rope choke and the presets). Click an airway to place one.
2. A wall is a resistance. Types with **Resistance** use a fixed R (Ns²/m⁸); *louvre* and *rope choke* use **free area** or **open %** and compute R from an orifice.
3. Type your own **Resistance** to replace the type's value. The panel says which value the solver uses.
4. A tighter seal has a larger R; an open door has R near 0.

## 8. Regulators
1. **Add regulator**, click an airway. Choose its *mode*:
   - **fixed-area**: a set opening, as an area (m²) or a % of the airway's section.
   - **target-dp**: holds a pressure drop (Pa).
   - **fixedFlow**: holds a flow (Fixed Q, m³/s). The air is forced through whatever the rest of the network does.
   - **fixedResistance**: a stated R.
2. *Status*: open, partial or closed. A closed regulator passes no air.

## 9. Coolers and heat
1. **Home → Add cooler**, click an airway. Then open the **Thermal** panel and pick what the cooler works to:
   - **Outlet target**: target dry and wet bulb, optionally limited to a capacity (kW). It only cools.
   - **Fixed duty**: a stated kW taken out of the air.
   - **Bulk air cooler (spray chamber)**: water in (°C), water flow (kg/s) and effectiveness (0–1). The air leaves saturated; the panel shows the water out temperature and the duty.
2. Rock and wall heat: age, **wetness** (a rating: Very dry 0, Dry 0.1, Damp 0.275, Wet 0.55, Very wet 0.85, or Custom), machines (kW, diesel), blasting (explosive kg, spread over), and heat per metre.
3. Read each airway's outlet wet bulb, **specific cooling power** and **wet kata** after solving. SCP below 300 W/m² is flagged.

## 10. Solve and check
- **Solve (F5)**. The log says *Converged*, *Converged with N warnings* (open the Solver log and read them) or what stopped it.
- *Check* lists disconnected nodes and airways with no resistance.
- Topology shows the tables (Air use, **Re-entry** after blasting). *Report* writes a PDF.
- Save from the File menu. The project keeps your fan tables and library items.
