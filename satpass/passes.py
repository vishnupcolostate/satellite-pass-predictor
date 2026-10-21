"""Pass prediction: when does a satellite rise, culminate, and set?

Algorithm
---------
1. Coarse scan: sample elevation every `step` seconds. A LEO pass lasts at
   least a few minutes, so a 30 s step will not skip over a real pass.
2. Each sign change of (elevation - horizon) brackets a rise or a set.
   Bisection narrows that bracket to < 1 s.
3. Between rise and set, elevation is unimodal, so a ternary search finds the
   time of maximum elevation (culmination).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, List, Optional

from . import frames
from .propagate import Satellite


@dataclass(frozen=True)
class Observer:
    lat: float
    lon: float
    alt_km: float = 0.0


@dataclass(frozen=True)
class Pass:
    rise: datetime
    culmination: datetime
    set: datetime
    rise_az: float
    max_el: float
    max_el_az: float
    set_az: float

    @property
    def duration_s(self) -> float:
        return (self.set - self.rise).total_seconds()


def look(sat: Satellite, obs: Observer, t: datetime):
    return frames.look_angles(obs.lat, obs.lon, obs.alt_km, sat.ecef(t))


def elevation(sat: Satellite, obs: Observer, t: datetime) -> float:
    return look(sat, obs, t)[1]


def _bisect(f: Callable[[datetime], float], lo: datetime, hi: datetime, tol_s: float) -> datetime:
    """Find the zero crossing of f between lo and hi (f(lo), f(hi) differ in sign)."""
    f_lo = f(lo)
    while (hi - lo).total_seconds() > tol_s:
        mid = lo + (hi - lo) / 2
        f_mid = f(mid)
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return lo + (hi - lo) / 2


def _argmax(f: Callable[[datetime], float], lo: datetime, hi: datetime, tol_s: float) -> datetime:
    """Ternary search for the maximum of a unimodal function."""
    while (hi - lo).total_seconds() > tol_s:
        third = (hi - lo) / 3
        m1, m2 = lo + third, hi - third
        if f(m1) < f(m2):
            lo = m1
        else:
            hi = m2
    return lo + (hi - lo) / 2


def find_passes(
    sat: Satellite,
    obs: Observer,
    start: datetime,
    hours: float = 24.0,
    min_max_el: float = 0.0,
    horizon: float = 0.0,
    step_s: float = 30.0,
    tol_s: float = 0.5,
) -> List[Pass]:
    """All passes in [start, start+hours] whose peak elevation >= min_max_el.

    A pass already in progress at `start` is reported with rise = start;
    one still in progress at the end is reported with set = end.
    """
    end = start + timedelta(hours=hours)
    step = timedelta(seconds=step_s)

    def above(t: datetime) -> float:
        return elevation(sat, obs, t) - horizon

    passes: List[Pass] = []
    t_prev, f_prev = start, above(start)
    rise: Optional[datetime] = start if f_prev > 0 else None

    t = start
    while t < end:
        t = min(t + step, end)
        f = above(t)
        if f_prev <= 0 < f:
            rise = _bisect(above, t_prev, t, tol_s)
        elif f_prev > 0 >= f and rise is not None:
            passes.append(_make_pass(sat, obs, rise, _bisect(above, t_prev, t, tol_s), tol_s))
            rise = None
        t_prev, f_prev = t, f

    if rise is not None:
        passes.append(_make_pass(sat, obs, rise, end, tol_s))

    return [p for p in passes if p.max_el >= min_max_el]


def _make_pass(sat: Satellite, obs: Observer, rise: datetime, set_: datetime, tol_s: float) -> Pass:
    culm = _argmax(lambda t: elevation(sat, obs, t), rise, set_, tol_s)
    rise_az, _, _ = look(sat, obs, rise)
    max_az, max_el, _ = look(sat, obs, culm)
    set_az, _, _ = look(sat, obs, set_)
    return Pass(rise, culm, set_, rise_az, max_el, max_az, set_az)
