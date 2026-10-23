ASM Lab sample projects
=======================

These open offline from inside ASM Lab: Mine > Load sample... (or Help > Tutorials).
The files here are the same projects, for use with File > Open.

Solver check cases (case01 ... case10)
  Small networks whose answer can be worked out by hand. Each file carries the
  expected result and the equation in its "expected" block. Solve (F5) and compare.

  01 single airway        R = k.L.per/A^3, Q = sqrt(dP/R)      279.5 m3/s, 11.18 m/s
  02 parallel             equal legs share the flow           279.5 m3/s each, 559.0 total
  03 series               one flow, drops add                 197.6 m3/s, 50 Pa each
  04 resistance override  a stated R beats geometry and k     44.72 m3/s
  05 fan curve            fan against a system resistance     53.45 m3/s
  06 two fans in series   pressures add at equal flow         66.67 m3/s
  07 two fans in parallel flows add at equal pressure         60.30 total, 30.15 each
  08 regulator            a leg held at a set flow            35.00 m3/s in that leg
  09 natural ventilation  density difference alone drives it  down S1, up S2
  10 symmetric ladder     regression case for the solver      converges quickly

  ASM Lab corrects resistance for the actual air density, so cases 01 and 02
  come out about 0.02% above the hand calculation. That is expected.

Thermal tests (thermal1 ... thermal5)
  Airflow and thermal solved together: set Solve mode to "Aero + thermal"
  (the sample list does it for you). Each file carries its site values
  (surface air, virgin rock) in "thermalSite"; ASM Lab shows them in the
  Thermal tab. 1000 m downcast, 1000 m drive at -1000 m, 1000 m upcast.

  1 autocompression      no rock heat               +9.79 kJ/kg down (+9.6 C), back at the top
  2 hot drive, dry rock  Gibson/Starfield, VRT 40 C t_out = VRT - (VRT - t_in).exp(-U.P.L/m.cp)
  3 hot drive, wet rock  half the wall wet          lower dry bulb, higher wet bulb than 2
  4 diesel and a cooler  300 kW x 0.6 / 0.33        545.5 kW; cooler to 18/12 C, condensate
  5 natural ventilation  3 MW in the drive, 150 Pa  more air with thermal than airflow alone

Mine layouts with block models
  Open the .asmlab.json, then the .dm with the same name (the sample list in
  ASM Lab opens both together). Each network is connected, with one intake,
  one exhaust, a main fan and a regulator. Grades and layouts are synthetic.

  copper_porphyry   66 nodes, 113 airways   flared stock; GRADE = Cu %, AU_GPT gold g/t
  ug2_reef          51 nodes,  59 airways   chromitite dipping 11 deg N, pothole, fault; GRADE = 4E g/t
  merensky_reef     46 nodes,  63 airways   dips 16 deg W with rolls, main reef + leader; GRADE = 4E g/t
  coal_seams       660 nodes, 1216 airways  three seams in a syncline, washout; GRADE = CV MJ/kg
  gold_vein        142 nodes, 159 airways   vein dipping 68 deg, plunging shoot; GRADE = Au g/t
  nickel_massive    24 nodes,  27 airways   massive keel under a halo; GRADE = Ni %

  The block models are DM .dm files. The view colours by GRADE; the other
  assay fields are in the file (Inspect > Colour by).

Other networks
  Untitled_Mine                             network project
  sample_test1 ... sample_test5             sample test networks (with the solver check cases)
  L1_L2_201308_VentDevel.dxf, Untitled_Mine_network.dxf   drawings to import
