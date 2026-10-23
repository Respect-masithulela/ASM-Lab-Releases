# Quick start

1. **New model.** Start ASM Lab, choose *New model*, name it. Or *Open model file* for a saved project, or *Import* for a DXF / spreadsheet.
2. **Draw.** Home → *Draw tunnel*; click points on the grid. Width and height are in the panel (a circular section shows one Diameter). *Add shaft*, *Curved tunnel*, *Place fan*, *Add wall*, *Add cooler* are in the same Create group. *Add node* cuts an airway where you click; *Fillet* and *Merge nodes* are in Edit.
3. **Boundaries.** Mark intake and exhaust nodes (Network tab) and set the surface air in the Thermal panel.
4. **Fans.** *Place fan*, then load a table (flow, pressure, efficiency) in *Fan curves*. State the air density the table was measured at.
5. **Solve.** Press **Solve (F5)**. The solver log says *Converged*, *Converged with N warnings* (read them) or why it did not.
6. **Heat.** Open the Thermal panel: rock, age, wetness (a rating from Very dry 0 to Very wet 0.85), machines, blasting, bulk air coolers. Results per airway include wet bulb, specific cooling power and wet kata.
7. **Re-entry.** Give airways with blasting an explosive mass; Topology → Re-entry shows the time to clear fumes.
8. **Save and report.** *File → Save*, or *Report* for a PDF.

Stuck? **Help** lists every button; **Report bug** reaches the team.
