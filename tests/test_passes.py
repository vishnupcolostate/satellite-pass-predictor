from datetime import datetime, timedelta, timezone

import pytest

from conftest import CSU, START
from satpass.passes import elevation, find_passes

# Peak times/elevations for ISS over CSU computed independently with Skyfield
# (EarthSatellite.find_events) from the same TLE. Used as a regression oracle.
SKYFIELD_PEAKS = [
    ("2026-10-20 13:07:09", 13.6), ("2026-10-20 14:45:03", 15.7),
    ("2026-10-20 16:22:29", 50.4), ("2026-10-20 17:59:02", 18.6),
    ("2026-10-21 09:05:27", 19.5), ("2026-10-21 10:42:02", 48.0),
    ("2026-10-21 12:19:29", 15.4), ("2026-10-21 13:57:23", 13.8),
    ("2026-10-21 15:34:59", 33.2), ("2026-10-21 17:11:46", 31.2),
    ("2026-10-21 18:47:40", 0.8), ("2026-10-22 08:18:14", 11.4),
    ("2026-10-22 09:54:35", 79.5), ("2026-10-22 11:31:50", 18.4),
]


@pytest.fixture(scope="module")
def passes(iss):
    return find_passes(iss, CSU, START, hours=48)


def test_matches_skyfield(passes):
    assert len(passes) == len(SKYFIELD_PEAKS)
    for p, (when, max_el) in zip(passes, SKYFIELD_PEAKS):
        expected = datetime.strptime(when, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        assert abs((p.culmination - expected).total_seconds()) < 3
        assert p.max_el == pytest.approx(max_el, abs=0.15)


def test_rise_and_set_are_on_horizon(iss, passes):
    for p in passes:
        assert p.rise < p.culmination < p.set
        assert elevation(iss, CSU, p.rise) == pytest.approx(0, abs=0.1)
        assert elevation(iss, CSU, p.set) == pytest.approx(0, abs=0.1)


def test_peak_is_a_maximum(iss, passes):
    for p in passes:
        for dt in (-20, 20):
            assert elevation(iss, CSU, p.culmination + timedelta(seconds=dt)) <= p.max_el


def test_min_elevation_filter(iss):
    high = find_passes(iss, CSU, START, hours=48, min_max_el=30)
    assert [round(p.max_el) for p in high] == [50, 48, 33, 31, 80]


def test_no_pass_missed_by_brute_force(iss):
    """A 5-second scan must not find any above-horizon interval the search missed."""
    found = find_passes(iss, CSU, START, hours=6)
    t, above, intervals = START, False, 0
    while t < START + timedelta(hours=6):
        now = elevation(iss, CSU, t) > 0
        intervals += now and not above
        above, t = now, t + timedelta(seconds=5)
    assert intervals == len(found)
