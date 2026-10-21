"""Thin wrapper around the SGP4 propagator.

SGP4 (Simplified General Perturbations 4) is the model TLEs are fit to. It
accounts for Earth's oblateness (J2-J4), atmospheric drag, and lunar/solar
effects for deep-space orbits. We use the `sgp4` package, a direct port of
Vallado's reference implementation, rather than re-implementing it.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

from sgp4.api import Satrec, jday

from . import frames
from .tle import Tle


class PropagationError(RuntimeError):
    pass


def julian(t: datetime) -> Tuple[float, float]:
    """Split Julian date (whole, fraction) for a timezone-aware datetime."""
    t = t.astimezone(timezone.utc)
    return jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)


class Satellite:
    def __init__(self, tle: Tle):
        self.tle = tle
        self.name = tle.name
        self._rec = Satrec.twoline2rv(tle.line1, tle.line2)

    def teme(self, t: datetime) -> frames.Vec3:
        jd, fr = julian(t)
        err, r, _v = self._rec.sgp4(jd, fr)
        if err != 0:
            raise PropagationError(f"SGP4 error code {err} for {self.name} at {t.isoformat()}")
        return tuple(r)  # type: ignore[return-value]

    def ecef(self, t: datetime) -> frames.Vec3:
        jd, fr = julian(t)
        return frames.teme_to_ecef(self.teme(t), jd + fr)

    def subpoint(self, t: datetime) -> Tuple[float, float, float]:
        """(lat deg, lon deg, altitude km) directly below the satellite."""
        return frames.ecef_to_geodetic(self.ecef(t))

    def epoch_age_days(self, t: datetime) -> float:
        return (t - self.tle.epoch).total_seconds() / 86400.0
