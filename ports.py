import csv
import math
import os

PORTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ports.csv")


def _load():
    if not os.path.exists(PORTS_FILE):
        raise FileNotFoundError(
            "data/ports.csv not found. Run: python make_ports.py path/to/WPI.csv"
        )
    with open(PORTS_FILE, newline="", encoding="utf-8") as f:
        return [(r["name"], float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f)]


PORTS = _load()


def distance_km(lat1, lon1, lat2, lon2):
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_port(lat, lon):
    """Return (name, distance_km) of the closest port."""
    best_name, best_d = None, float("inf")
    for name, plat, plon in PORTS:
        if abs(plat - lat) * 111 > best_d:  # too far north/south to beat the best so far
            continue
        d = distance_km(lat, lon, plat, plon)
        if d < best_d:
            best_name, best_d = name, d
    return best_name, best_d