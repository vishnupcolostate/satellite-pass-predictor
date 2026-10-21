"""Two-Line Element (TLE) parsing, validation, and fetching.

A TLE is the standard format NORAD/Space Force uses to publish the orbit of
every tracked object. Each record is an optional name line plus two 69-char
lines. Column 69 of each line is a mod-10 checksum.
"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"


class TleError(ValueError):
    """Raised when a TLE record is malformed."""


@dataclass(frozen=True)
class Tle:
    name: str
    line1: str
    line2: str

    @property
    def norad_id(self) -> int:
        return int(self.line1[2:7])

    @property
    def epoch(self) -> datetime:
        """Epoch encoded in line 1, columns 19-32 (YYDDD.DDDDDDDD)."""
        yy = int(self.line1[18:20])
        day_of_year = float(self.line1[20:32])
        year = 2000 + yy if yy < 57 else 1900 + yy
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        return start + timedelta(days=day_of_year - 1)


def checksum(line: str) -> int:
    """Mod-10 checksum: sum of digits, with each '-' counting as 1."""
    total = 0
    for ch in line[:68]:
        if ch.isdigit():
            total += int(ch)
        elif ch == "-":
            total += 1
    return total % 10


def validate(line1: str, line2: str) -> None:
    for number, line in ((1, line1), (2, line2)):
        if len(line) < 69:
            raise TleError(f"line {number} is {len(line)} chars, expected 69")
        if not line.startswith(f"{number} "):
            raise TleError(f"line {number} must start with '{number} '")
        if checksum(line) != int(line[68]):
            raise TleError(f"line {number} checksum mismatch: {line!r}")
    if line1[2:7] != line2[2:7]:
        raise TleError("catalog numbers on line 1 and line 2 differ")


def parse(text: str) -> List[Tle]:
    """Parse 2-line or 3-line TLE text into a list of records."""
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    records: List[Tle] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("1 ") and i + 1 < len(lines) and lines[i + 1].startswith("2 "):
            name, l1, l2 = lines[i][2:7].strip(), lines[i], lines[i + 1]
            i += 2
        elif i + 2 < len(lines):
            name, l1, l2 = lines[i].strip(), lines[i + 1], lines[i + 2]
            i += 3
        else:
            raise TleError(f"incomplete TLE record starting at: {lines[i]!r}")
        validate(l1, l2)
        records.append(Tle(name, l1, l2))
    return records


def load(path: str | Path) -> List[Tle]:
    return parse(Path(path).read_text())


def fetch(group: str = "stations", timeout: float = 15.0) -> List[Tle]:
    """Download current TLEs for a CelesTrak group (e.g. 'stations', 'visual')."""
    req = urllib.request.Request(
        CELESTRAK_URL.format(group=group),
        headers={"User-Agent": "satellite-pass-predictor"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return parse(resp.read().decode("ascii"))


def find(records: List[Tle], query: str) -> Tle:
    """Look up a satellite by NORAD id or case-insensitive name substring."""
    if query.isdigit():
        for rec in records:
            if rec.norad_id == int(query):
                return rec
    q = query.lower()
    for rec in records:
        if q in rec.name.lower():
            return rec
    raise KeyError(f"no satellite matching {query!r}")
