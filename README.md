# CargoLens

**Live demo:** https://cargolens-sii0.onrender.com/map/ (free hosting: the first load can take up to a minute, and ships update while the page is open)

A live vessel-tracking and alerting backend. It streams real AIS ship positions, stores them in MySQL, flags suspicious behaviour, and shows everything on an interactive map.

![CargoLens map](docs/map.png)

## What it does

- Continuously ingests live ship positions from the AISStream.io WebSocket feed, in a background task inside the API
- Refreshes the map every 30 seconds, moving ships in place
- Stores vessels, positions and alerts in MySQL via SQLAlchemy
- Flags ships that are stopped offshore (far from any known port) or moving unusually fast
- Serves a REST API (FastAPI) with auto-generated docs at `/docs`
- Shows ships on a Leaflet map, with alerts highlighted in red

## Tech stack

Python 3.13, FastAPI, SQLAlchemy, MySQL, WebSockets, Leaflet.js

## Run it locally

1. Clone the repo and create a virtual environment: `python3 -m venv venv && source venv/bin/activate`
2. Install dependencies: `pip install fastapi uvicorn sqlalchemy pymysql httpx python-dotenv websockets certifi`
3. Create a MySQL database called `cargolens`
4. Create a `.env` file with `DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/cargolens` and `AISSTREAM_API_KEY=your_key`
5. Collect ship data: `python ingest.py`
6. Run the alert checks: `python alerts.py`
7. Start the API: `uvicorn main:app --reload`, then open `http://127.0.0.1:8000/map/`

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /vessels` | Latest position of every tracked vessel |
| `GET /alerts` | Most recent alerts |
| `GET /docs` | Interactive API documentation |

## Known limitations and next steps
## Known limitations and next steps

- The port list is hand-picked (23 ports), so ships docked at unlisted harbours can trigger false "stopped offshore" alerts; next step is loading a full open port and anchorage dataset
- On free hosting the server sleeps when idle, so ingestion only runs while someone is viewing the map; a paid worker would run it 24/7
- "Silent ship" detection (a vessel stops transmitting) is possible now that ingestion is continuous
- Planned: ETA delay prediction and Docker deployment
