import math

import pytest

from satpass import frames


def test_gmst_at_j2000():
    # Known value: GMST at 2000-01-01 12:00 UT1 is 280.46061837 deg.
    assert math.degrees(frames.gmst(2451545.0)) == pytest.approx(280.46061837, abs=1e-6)


@pytest.mark.parametrize("lat,lon,alt", [(40.5734, -105.0865, 1.525), (-33.9, 151.2, 0.0),
                                         (89.9, 10.0, 400.0), (0.0, 179.9, 35786.0)])
def test_geodetic_round_trip(lat, lon, alt):
    back = frames.ecef_to_geodetic(frames.geodetic_to_ecef(lat, lon, alt))
    assert back == pytest.approx((lat, lon, alt), abs=1e-7)


def test_overhead_target_is_at_zenith():
    target = frames.geodetic_to_ecef(40.0, -105.0, 400.0)
    _, el, rng = frames.look_angles(40.0, -105.0, 0.0, target)
    assert el == pytest.approx(90.0, abs=1e-6)
    assert rng == pytest.approx(400.0, abs=1e-6)


def test_target_due_east_on_equator():
    target = frames.geodetic_to_ecef(0.0, 1.0, 0.0)
    az, el, _ = frames.look_angles(0.0, 0.0, 0.0, target)
    assert az == pytest.approx(90.0, abs=1e-6)
    assert el < 0  # Earth curves away, so it sits just below the horizon
