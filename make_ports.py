"""One-off helper: turns the raw World Port Index CSV into a slim data/ports.csv.

Usage:  python make_ports.py path/to/WPI.csv
"""
import csv
import os
import sys

if len(sys.argv) != 2:
    sys.exit("Usage: python make_ports.py path/to/WPI.csv")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ports.csv")


def find(headers, exact, partial):
    low = {h.lower().strip(): h for h in headers}
    for c in exact:
        if c in low:
            return low[c]
    for c in partial:
        for k, h in low.items():
            if c in k:
                return h
    return None


with open(sys.argv[1], newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames or []
    name_col = find(headers, ["main port name", "port name", "name"], ["port name"])
    lat_col = find(headers, ["latitude", "lat"], ["latitude"])
    lon_col = find(headers, ["longitude", "lon", "long"], ["longitude"])
    if not (name_col and lat_col and lon_col):
        print("Could not find the columns. Headers in your file are:")
        for h in headers:
            print("  -", h)
        sys.exit(1)
    rows = []
    for r in reader:
        try:
            lat, lon = float(r[lat_col]), float(r[lon_col])
        except (TypeError, ValueError):
            continue
        if abs(lat) > 90 or abs(lon) > 180:
            continue
        rows.append((r[name_col].strip(), round(lat, 4), round(lon, 4)))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["name", "lat", "lon"])
    w.writerows(rows)
print(f"Saved {len(rows)} ports to {OUT}")