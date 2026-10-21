"""Command-line interface.

    python -m satpass passes --sat ISS --lat 40.5734 --lon -105.0865
    python -m satpass track  --sat ISS --minutes 186 --out web/track.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from . import tle as tlemod
from .groundtrack import ground_track, split_antimeridian
from .passes import Observer, find_passes
from .propagate import Satellite

SAMPLE_TLE = Path(__file__).resolve().parent.parent / "data" / "stations.tle"

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass(az: float) -> str:
    return COMPASS[int((az + 11.25) // 22.5) % 16]


def _load_satellite(args) -> Satellite:
    records = tlemod.fetch(args.fetch) if args.fetch else tlemod.load(args.tle)
    sat = Satellite(tlemod.find(records, args.sat))
    return sat


def _start(args) -> datetime:
    if args.start:
        t = datetime.fromisoformat(args.start)
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _warn_stale(sat: Satellite, t: datetime) -> None:
    age = sat.epoch_age_days(t)
    if abs(age) > 7:
        print(f"warning: TLE epoch is {age:.1f} days from start time; "
              f"accuracy degrades quickly. Use --fetch for fresh elements.", file=sys.stderr)


def cmd_passes(args) -> None:
    sat, start = _load_satellite(args), _start(args)
    _warn_stale(sat, start)
    obs = Observer(args.lat, args.lon, args.alt / 1000.0)
    passes = find_passes(sat, obs, start, args.hours, min_max_el=args.min_el)
    print(f"{sat.name} (NORAD {sat.tle.norad_id}) passes over "
          f"({args.lat:.4f}, {args.lon:.4f}), next {args.hours:g} h, peak >= {args.min_el:g} deg\n")
    print(f"{'Rise (UTC)':<20} {'Az':>4}  {'Peak (UTC)':<20} {'El':>5} {'Az':>4}  "
          f"{'Set (UTC)':<20} {'Az':>4}  {'Dur':>6}")
    for p in passes:
        print(f"{p.rise:%Y-%m-%d %H:%M:%S} {compass(p.rise_az):>4}  "
              f"{p.culmination:%Y-%m-%d %H:%M:%S} {p.max_el:5.1f} {compass(p.max_el_az):>4}  "
              f"{p.set:%Y-%m-%d %H:%M:%S} {compass(p.set_az):>4}  "
              f"{int(p.duration_s // 60):>3}m{int(p.duration_s % 60):02d}s")
    if not passes:
        print("(no passes)")


def cmd_track(args) -> None:
    sat, start = _load_satellite(args), _start(args)
    _warn_stale(sat, start)
    obs = Observer(args.lat, args.lon, args.alt / 1000.0)
    track = ground_track(sat, start, args.minutes, args.step)
    passes = find_passes(sat, obs, start, args.hours, min_max_el=args.min_el)
    doc = {
        "satellite": {"name": sat.name, "norad_id": sat.tle.norad_id,
                      "tle_epoch": sat.tle.epoch.isoformat()},
        "observer": {"lat": args.lat, "lon": args.lon, "alt_m": args.alt},
        "start": start.isoformat(),
        "segments": [[[lat, lon] for _, lat, lon, _ in seg] for seg in split_antimeridian(track)],
        "points": [{"t": t, "lat": lat, "lon": lon, "alt_km": alt} for t, lat, lon, alt in track],
        "passes": [{
            "rise": p.rise.isoformat(), "culmination": p.culmination.isoformat(),
            "set": p.set.isoformat(), "max_el": round(p.max_el, 2),
            "rise_az": round(p.rise_az, 1), "set_az": round(p.set_az, 1),
            "duration_s": round(p.duration_s),
        } for p in passes],
    }
    with open(args.out, "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"wrote {len(track)} track points and {len(passes)} passes to {args.out}")


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--sat", default="ISS", help="NORAD id or name substring (default: ISS)")
    common.add_argument("--tle", default=str(SAMPLE_TLE), help="TLE file to read (default: bundled sample)")
    common.add_argument("--fetch", metavar="GROUP", help="download fresh TLEs from CelesTrak instead")
    common.add_argument("--lat", type=float, default=40.5734, help="observer latitude (default: CSU)")
    common.add_argument("--lon", type=float, default=-105.0865, help="observer longitude")
    common.add_argument("--alt", type=float, default=1525.0, help="observer altitude, meters")
    common.add_argument("--start", help="ISO start time, UTC (default: now)")
    common.add_argument("--hours", type=float, default=48.0, help="search window for passes")
    common.add_argument("--min-el", type=float, default=10.0, help="minimum peak elevation, deg")

    parser = argparse.ArgumentParser(prog="satpass", description="Satellite pass predictor")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("passes", parents=[common], help="list upcoming passes")
    p.set_defaults(func=cmd_passes)
    t = sub.add_parser("track", parents=[common], help="export ground track + passes as JSON")
    t.add_argument("--minutes", type=float, default=186.0, help="track length (default: 2 orbits)")
    t.add_argument("--step", type=float, default=30.0, help="track sample step, seconds")
    t.add_argument("--out", default="web/track.json")
    t.set_defaults(func=cmd_track)
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)
