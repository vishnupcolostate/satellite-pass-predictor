"""Ground track: the path traced on Earth by the point directly below a satellite."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Tuple

from .propagate import Satellite

TrackPoint = Tuple[str, float, float, float]  # (iso time, lat, lon, alt km)


def ground_track(sat: Satellite, start: datetime, minutes: float, step_s: float = 30.0) -> List[TrackPoint]:
    points: List[TrackPoint] = []
    n = int(minutes * 60 / step_s)
    for i in range(n + 1):
        t = start + timedelta(seconds=i * step_s)
        lat, lon, alt = sat.subpoint(t)
        points.append((t.isoformat(), lat, lon, alt))
    return points


def split_antimeridian(points: List[TrackPoint]) -> List[List[TrackPoint]]:
    """Break the track where longitude wraps +180 -> -180 so maps don't draw a line across."""
    segments: List[List[TrackPoint]] = [[]]
    for p in points:
        if segments[-1] and abs(p[2] - segments[-1][-1][2]) > 180:
            segments.append([])
        segments[-1].append(p)
    return segments
