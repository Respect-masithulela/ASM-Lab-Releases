"""Moist-air density from pressure, dry bulb and wet bulb (the source tool input node conditions), for converting the source tool mass-flow inputs
(kg/s) to volume flow without using the source tool's solution.  rho = (P - pv) / (Ra T) + pv / (Rv T)
pv from the psychrometer equation pv = ps(WB) - 6.62e-4 P (DB - WB), ps by Tetens (kPa)."""
import math


def ps(t): return 0.6108 * math.exp(17.27 * t / (t + 237.3))


def rho(P_kPa, db, wb):
    pv = max(ps(wb) - 6.62e-4 * P_kPa * (db - wb), 0.0)
    T = db + 273.15
    return (P_kPa - pv) * 1000 / (287.05 * T) + pv * 1000 / (461.5 * T)
