import pytest

from satpass import tle

L1 = "1 25544U 98067A   26293.53177616  .00007749  00000+0  14885-3 0  9993"
L2 = "2 25544  51.6327  39.8161 0006774 287.4911  72.5337 15.48956417591181"


def test_checksum_matches_last_column():
    assert tle.checksum(L1) == 3
    assert tle.checksum(L2) == 1


def test_bad_checksum_rejected():
    with pytest.raises(tle.TleError):
        tle.validate(L1[:68] + "0", L2)


def test_parse_three_line_and_two_line():
    three = tle.parse(f"ISS (ZARYA)\n{L1}\n{L2}\n")
    two = tle.parse(f"{L1}\n{L2}\n")
    assert three[0].name == "ISS (ZARYA)"
    assert two[0].norad_id == three[0].norad_id == 25544


def test_epoch_decoded():
    rec = tle.Tle("ISS", L1, L2)
    assert (rec.epoch.year, rec.epoch.month, rec.epoch.day) == (2026, 10, 20)


def test_sample_file_loads(records):
    assert len(records) == 17
    assert tle.find(records, "iss").norad_id == 25544
    with pytest.raises(KeyError):
        tle.find(records, "not a satellite")
