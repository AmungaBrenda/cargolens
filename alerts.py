import math

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import engine
from models import Vessel, Position, Alert

FAST_KNOTS = 25
STOPPED_KNOTS = 0.5
PORT_RADIUS_KM = 5

PORTS = {
    "Dover": (51.127, 1.322), "Calais": (50.967, 1.850),
    "Dunkirk": (51.050, 2.370), "Zeebrugge": (51.330, 3.200),
    "Ostend": (51.230, 2.920), "Boulogne": (50.730, 1.600),
    "Dieppe": (49.930, 1.080), "Le Havre": (49.480, 0.110),
    "Rouen": (49.440, 1.090), "Paris": (48.860, 2.300),
    "Cherbourg": (49.650, -1.620), "Southampton": (50.900, -1.400),
    "Portsmouth": (50.800, -1.100), "Poole": (50.710, -1.990),
    "Plymouth": (50.360, -4.130), "Newhaven": (50.790, 0.060),
    "Shoreham": (50.830, -0.250), "Ramsgate": (51.330, 1.420),
    "Tilbury": (51.455, 0.355), "Felixstowe": (51.950, 1.350),
    "Harwich": (51.950, 1.290), "Avonmouth": (51.500, -2.710),
    "St Peter Port": (49.456, -2.536),
}


def distance_km(lat1, lon1, lat2, lon2):
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_port(lat, lon):
    name, d = min(
        ((n, distance_km(lat, lon, plat, plon)) for n, (plat, plon) in PORTS.items()),
        key=lambda x: x[1],
    )
    return name, d


def run_checks():
    created = 0
    with Session(engine) as session:
        latest = (
            session.query(Position.vessel_id, func.max(Position.id).label("pid"))
            .group_by(Position.vessel_id)
            .subquery()
        )
        rows = (
            session.query(Vessel, Position)
            .join(latest, Vessel.id == latest.c.vessel_id)
            .join(Position, Position.id == latest.c.pid)
            .all()
        )
        for vessel, pos in rows:
            speed = pos.speed_knots
            if speed is None or speed >= 102:
                continue
            port, dist = nearest_port(pos.latitude, pos.longitude)
            if speed >= FAST_KNOTS:
                kind = "HIGH_SPEED"
                msg = f"{vessel.name} is moving at {speed} knots"
            elif speed <= STOPPED_KNOTS and dist > PORT_RADIUS_KM:
                kind = "STOPPED_OFFSHORE"
                msg = f"{vessel.name} is stopped {dist:.0f} km from {port}"
            else:
                continue
            exists = session.query(Alert).filter_by(vessel_id=vessel.id, alert_type=kind).first()
            if not exists:
                session.add(Alert(vessel_id=vessel.id, alert_type=kind, message=msg))
                created += 1
        session.commit()
    return created


if __name__ == "__main__":
    print("New alerts:", run_checks())