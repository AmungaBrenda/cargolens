from fastapi import FastAPI

app = FastAPI(title="CargoLens")

@app.get("/")
def home():
    return {"status": "CargoLens is alive!"}


from sqlalchemy import text
from database import engine 

@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return {"database": "Database is connected!"}
    

from models import Base
Base.metadata.create_all(engine)

from sqlalchemy import func
from sqlalchemy.orm import Session
from models import Vessel, Position


@app.get("/vessels")
def list_vessels():
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
        alert_by_vessel = {a.vessel_id: a.message for a in session.query(Alert).all()}
        return [
            {"mmsi": v.mmsi, "name": v.name, "lat": p.latitude, "lon": p.longitude,
             "speed": p.speed_knots, "alert": alert_by_vessel.get(v.id)}
            for v, p in rows
        ]
        


from fastapi.staticfiles import StaticFiles

app.mount("/map", StaticFiles(directory="static", html=True), name="map")   


from models import Alert


@app.get("/alerts")
def list_alerts():
    with Session(engine) as session:
        alerts = session.query(Alert).order_by(Alert.id.desc()).limit(50).all()
        return [
            {"type": a.alert_type, "message": a.message, "created_at": str(a.created_at)}
            for a in alerts
        ]