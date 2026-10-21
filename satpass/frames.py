"""Coordinate frames: TEME -> ECEF -> geodetic, and observer look angles.

SGP4 outputs positions in TEME (True Equator, Mean Equinox), an inertial
frame. To know where a satellite is over the Earth we rotate by the Earth's
sidereal angle (GMST) into ECEF, which spins with the planet. From ECEF we can
get latitude/longitude, or the azimuth/elevation seen by a ground observer.

Polar motion and UT1-UTC are ignored; the error that introduces (~tens of
meters) is far below SGP4's own accuracy (~1 km at epoch).
"""
from __future__ import annotations

import math
from typing import Tuple

Vec3 = Tuple[float, float, float]

# WGS-84 ellipsoid
WGS84_A = 6378.137  # equatorial radius, km
WGS84_F = 1 / 298.257223563
WGS84_E2 = WGS84_F * (2 - WGS84_F)  # first eccentricity squared

TWO_PI = 2 * math.pi


def gmst(jd_ut1: float) -> float:
    """Greenwich Mean Sidereal Time in radians (IAU-82, as used by SGP4)."""
    t = (jd_ut1 - 2451545.0) / 36525.0
    seconds = (
        -6.2e-6 * t ** 3
        + 0.093104 * t ** 2
        + (876600.0 * 3600 + 8640184.812866) * t
        + 67310.54841
    )
    return math.radians(seconds / 240.0) % TWO_PI


def teme_to_ecef(r: Vec3, jd_ut1: float) -> Vec3:
    """Rotate a TEME position about the z axis by -GMST."""
    theta = gmst(jd_ut1)
    c, s = math.cos(theta), math.sin(theta)
    x, y, z = r
    return (c * x + s * y, -s * x + c * y, z)


def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_km: float) -> Vec3:
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * math.sin(lat) ** 2)
    return (
        (n + alt_km) * math.cos(lat) * math.cos(lon),
        (n + alt_km) * math.cos(lat) * math.sin(lon),
        (n * (1 - WGS84_E2) + alt_km) * math.sin(lat),
    )


def ecef_to_geodetic(r: Vec3) -> Tuple[float, float, float]:
    """ECEF (km) -> (lat deg, lon deg, alt km), iterating on latitude."""
    x, y, z = r
    lon = math.atan2(y, x)
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1 - WGS84_E2))
    for _ in range(10):
        n = WGS84_A / math.sqrt(1 - WGS84_E2 * math.sin(lat) ** 2)
        alt = p / math.cos(lat) - n
        new_lat = math.atan2(z, p * (1 - WGS84_E2 * n / (n + alt)))
        if abs(new_lat - lat) < 1e-12:
            lat = new_lat
            break
        lat = new_lat
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * math.sin(lat) ** 2)
    alt = p / math.cos(lat) - n
    return math.degrees(lat), math.degrees(lon), alt


def look_angles(
    lat_deg: float, lon_deg: float, alt_km: float, target_ecef: Vec3
) -> Tuple[float, float, float]:
    """Azimuth (deg, from north, clockwise), elevation (deg), range (km)."""
    ox, oy, oz = geodetic_to_ecef(lat_deg, lon_deg, alt_km)
    dx, dy, dz = target_ecef[0] - ox, target_ecef[1] - oy, target_ecef[2] - oz
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    sl, cl = math.sin(lat), math.cos(lat)
    so, co = math.sin(lon), math.cos(lon)
    # Rotate the line-of-sight vector into local East-North-Up.
    east = -so * dx + co * dy
    north = -sl * co * dx - sl * so * dy + cl * dz
    up = cl * co * dx + cl * so * dy + sl * dz
    rng = math.sqrt(dx * dx + dy * dy + dz * dz)
    az = math.degrees(math.atan2(east, north)) % 360.0
    el = math.degrees(math.asin(up / rng))
    return az, el, rng
