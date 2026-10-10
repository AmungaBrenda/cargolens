import asyncio
import json
import os
import ssl
import time

import certifi
import websockets
from sqlalchemy import text
from sqlalchemy.orm import Session

from alerts import run_checks
from database import engine
from models import Position, Vessel

BOUNDING_BOX = [[[48.0, -6.0], [53.0, 3.0]]]
LISTEN_SECONDS = 25      # how long to listen each round
PAUSE_SECONDS = 35       # rest between rounds
SAVE_EVERY_SECONDS = 60  # save at most one position per ship per minute
KEEP_HOURS = 6           # delete positions older than this

ssl_context = ssl.create_default_context(cafile=certifi.where())
last_saved = {}


def save(meta, report):
    with Session(engine) as session:
        mmsi = str(meta["MMSI"])
        vessel = session.query(Vessel).filter_by(mmsi=mmsi).first()
        if not vessel:
            name = (meta.get("ShipName") or "Unknown").strip() or "Unknown"
            vessel = Vessel(mmsi=mmsi, name=name)
            session.add(vessel)
            session.flush()
        session.add(Position(
            vessel_id=vessel.id,
            latitude=meta["latitude"],
            longitude=meta["longitude"],
            speed_knots=report.get("Sog"),
            nav_status=report.get("NavigationalStatus"),
        ))
        session.commit()


def tidy_and_check():
    with engine.begin() as conn:
        conn.execute(text(
            f"DELETE FROM positions WHERE recorded_at < NOW() - INTERVAL {KEEP_HOURS} HOUR"
        ))
    run_checks()


async def listen_once():
    url = "wss://stream.aisstream.io/v0/stream"
    async with websockets.connect(url, ssl=ssl_context) as ws:
        await ws.send(json.dumps({
            "APIKey": os.getenv("AISSTREAM_API_KEY"),
            "BoundingBoxes": BOUNDING_BOX,
            "FilterMessageTypes": ["PositionReport"],
        }))
        deadline = time.time() + LISTEN_SECONDS
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=deadline - time.time())
            except asyncio.TimeoutError:
                break
            msg = json.loads(raw)
            if "MetaData" not in msg:
                continue
            meta = msg["MetaData"]
            report = msg["Message"]["PositionReport"]
            mmsi = str(meta["MMSI"])
            now = time.time()
            if now - last_saved.get(mmsi, 0) < SAVE_EVERY_SECONDS:
                continue
            last_saved[mmsi] = now
            await asyncio.to_thread(save, meta, report)


async def run_forever():
    while True:
        try:
            await listen_once()
            await asyncio.to_thread(tidy_and_check)
        except Exception as e:
            print("live ingest error:", e)
        await asyncio.sleep(PAUSE_SECONDS)