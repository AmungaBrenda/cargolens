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
        return [
            {"mmsi": v.mmsi, "name": v.name, "lat": p.latitude,
             "lon": p.longitude, "speed": p.speed_knots}
            for v, p in rows
        ]


from fastapi.staticfiles import StaticFiles

app.mount("/map", StaticFiles(directory="static", html=True), name="map")    