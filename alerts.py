from sqlalchemy import func
from sqlalchemy.orm import Session

from database import engine
from models import Vessel, Position, Alert
from ports import nearest_port

FAST_KNOTS = 25
STOPPED_KNOTS = 0.5
PORT_RADIUS_KM = 10

# AIS navigational status codes for ships that are *supposed* to be stationary:
# 1 = at anchor, 5 = moored, 7 = engaged in fishing
EXPECTED_TO_STOP = {1, 5, 7}


def run_checks():
    created = 0
    with Session(engine) as session:
        session.query(Alert).delete()  # alerts always reflect the current situation
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
            if speed >= FAST_KNOTS:
                kind = "HIGH_SPEED"
                msg = f"{vessel.name} is moving at {speed} knots"
            elif speed <= STOPPED_KNOTS and pos.nav_status not in EXPECTED_TO_STOP:
                port, dist = nearest_port(pos.latitude, pos.longitude)
                if dist <= PORT_RADIUS_KM:
                    continue
                kind = "STOPPED_OFFSHORE"
                msg = f"{vessel.name} is stopped {dist:.0f} km from {port}"
            else:
                continue
            session.add(Alert(vessel_id=vessel.id, alert_type=kind, message=msg))
            created += 1
        session.commit()
    return created


if __name__ == "__main__":
    print("New alerts:", run_checks())