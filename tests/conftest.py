from datetime import datetime, timezone
from pathlib import Path

import pytest

from satpass import tle
from satpass.passes import Observer
from satpass.propagate import Satellite

DATA = Path(__file__).resolve().parent.parent / "data" / "stations.tle"

# Fixed inputs so every test is deterministic (TLE epoch is 2026-10-20).
START = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
CSU = Observer(40.5734, -105.0865, 1.525)


@pytest.fixture(scope="session")
def records():
    return tle.load(DATA)


@pytest.fixture(scope="session")
def iss(records):
    return Satellite(tle.find(records, "25544"))
