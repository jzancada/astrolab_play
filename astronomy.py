"""
Coordinate transforms and astronomical data for the interactive astrolabe.
"""
import math

OBL     = 23.4393           # obliquity of ecliptic (degrees)
OBL_R   = math.radians(OBL)

def _cap_r():
    d = math.radians(-OBL)
    return math.cos(d) / (1.0 + math.sin(d))

CAPRICORN_R = _cap_r()      # ~1.5243 — natural radius of Tropic of Capricorn


# ── stereographic projection ──────────────────────────────────────────────────

def stereo(ha_deg, dec_deg):
    """
    Stereographic projection from the south celestial pole onto the equatorial plane.
    Convention: ha=0 → south (bottom), ha increases clockwise (westward).
    Returns (x, y) in projection units.  North pole → origin.
    to_screen: sx = cx + x*scale,  sy = cy - y*scale
    Returns (1e9, 1e9) for points at/near the south pole (projection center).
    """
    d = math.radians(dec_deg)
    denom = 1.0 + math.sin(d)
    if denom < 1e-9:
        return 1e9, 1e9      # south pole maps to infinity — will be clipped
    h = math.radians(ha_deg)
    r = math.cos(d) / denom
    return r * math.sin(h), -r * math.cos(h)


def to_screen(px, py, cx, cy, scale):
    return int(cx + px * scale), int(cy - py * scale)


# ── sun ───────────────────────────────────────────────────────────────────────

def sun_lon(day):
    """Approximate solar ecliptic longitude (degrees) for day of year 1–365."""
    return (day - 80.0) * 360.0 / 365.25 % 360.0


# ── coordinate transforms ─────────────────────────────────────────────────────

def ecl_to_equ(lon_deg, lat_deg=0.0):
    """Ecliptic (lon, lat) → equatorial (RA_deg, Dec_deg)."""
    lon = math.radians(lon_deg)
    lat = math.radians(lat_deg)
    sd  = (math.sin(lat) * math.cos(OBL_R) +
           math.cos(lat) * math.sin(OBL_R) * math.sin(lon))
    dec = math.asin(max(-1.0, min(1.0, sd)))
    y   = math.sin(lon) * math.cos(OBL_R) - math.tan(lat) * math.sin(OBL_R)
    ra  = math.degrees(math.atan2(y, math.cos(lon))) % 360.0
    return ra, math.degrees(dec)


def hor_to_equ(alt_deg, az_deg, lat_deg):
    """
    Horizon (Alt, Az from North clockwise) → equatorial (HA_deg, Dec_deg).
    """
    alt = math.radians(alt_deg)
    az  = math.radians(az_deg)
    lat = math.radians(lat_deg)
    sd  = (math.sin(alt) * math.sin(lat) +
           math.cos(alt) * math.cos(lat) * math.cos(az))
    dec = math.asin(max(-1.0, min(1.0, sd)))
    cd, cl = math.cos(dec), math.cos(lat)
    if abs(cd * cl) < 1e-9:
        return 0.0, math.degrees(dec)
    sha = -math.sin(az) * math.cos(alt) / cd
    cha = (math.sin(alt) - math.sin(dec) * math.sin(lat)) / (cd * cl)
    return math.degrees(math.atan2(sha, cha)) % 360.0, math.degrees(dec)


def equ_to_hor(ha_deg, dec_deg, lat_deg):
    """Equatorial (HA_deg, Dec_deg) → horizon (Alt_deg, Az_deg N-clockwise)."""
    ha  = math.radians(ha_deg)
    dec = math.radians(dec_deg)
    lat = math.radians(lat_deg)
    sa  = (math.sin(dec) * math.sin(lat) +
           math.cos(dec) * math.cos(lat) * math.cos(ha))
    alt = math.asin(max(-1.0, min(1.0, sa)))
    y   = -math.cos(dec) * math.sin(ha)
    x   = math.sin(dec) * math.cos(lat) - math.cos(dec) * math.sin(lat) * math.cos(ha)
    return math.degrees(alt), math.degrees(math.atan2(y, x)) % 360.0


def ra_dec_to_xyz(ra_deg, dec_deg):
    """Unit-sphere point in equatorial frame (X=RA0, Y=RA90°, Z=NCP)."""
    ra = math.radians(ra_deg)
    d  = math.radians(dec_deg)
    return math.cos(d)*math.cos(ra), math.cos(d)*math.sin(ra), math.sin(d)


# ── star catalogue ─────────────────────────────────────────────────────────────
# (name, RA_deg, Dec_deg)
STARS = [
    ("Sirius",     101.29, -16.72),
    ("Canopus",     95.99, -52.70),
    ("Arcturus",   213.92,  19.18),
    ("Vega",       279.23,  38.78),
    ("Capella",     79.17,  45.99),
    ("Rigel",       78.63,  -8.20),
    ("Procyon",    114.83,   5.23),
    ("Betelgeuse",  88.79,   7.41),
    ("Altair",     297.69,   8.87),
    ("Aldebaran",   68.98,  16.51),
    ("Antares",    247.35, -26.43),
    ("Spica",      201.30, -11.16),
    ("Pollux",     116.33,  28.03),
    ("Fomalhaut",  344.41, -29.62),
    ("Deneb",      310.36,  45.28),
    ("Regulus",    152.09,  11.97),
]
