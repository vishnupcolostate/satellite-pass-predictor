from datetime import timedelta

from conftest import START


def test_iss_altitude_stays_in_leo(iss):
    for minute in range(0, 93, 3):
        _, _, alt = iss.subpoint(START + timedelta(minutes=minute))
        assert 380 < alt < 450


def test_iss_latitude_bounded_by_inclination(iss):
    lats = [iss.subpoint(START + timedelta(minutes=m))[0] for m in range(0, 93)]
    # Inclination (51.63 deg) bounds *geocentric* latitude. Geodetic latitude is
    # measured against the flattened ellipsoid, so it peaks a little higher.
    assert max(lats) <= 52.0 and min(lats) >= -52.0
    assert max(lats) > 50 and min(lats) < -50  # it does reach near the inclination
