import asyncio
import json
import os
import ssl
import certifi

ssl_context = ssl.create_default_context(cafile=certifi.where())


import websockets
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from database import engine
from models import Vessel, Position

load_dotenv()
API_KEY = os.getenv("AISSTREAM_API_KEY")
MAX_MESSAGES = 50


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
        ))
        session.commit()


async def collect():
   async with websockets.connect("wss://stream.aisstream.io/v0/stream", ssl=ssl_context) as ws:
        await ws.send(json.dumps({
            "APIKey": API_KEY,
            "BoundingBoxes": [[[48.0, -6.0], [53.0, 3.0]]],
            "FilterMessageTypes": ["PositionReport"],
        }))
        count = 0
        async for raw in ws:
            msg = json.loads(raw)
            if "MetaData" not in msg:
                print("Server said:", msg)
                continue
            meta = msg["MetaData"]
            report = msg["Message"]["PositionReport"]
            save(meta, report)
            count += 1
            print(count, meta.get("ShipName", "").strip(), meta["latitude"], meta["longitude"])
            if count >= MAX_MESSAGES:
                break


asyncio.run(collect())