import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

connect_args = {}
ca_file = os.getenv("DB_SSL_CA")
if ca_file:
    connect_args["ssl"] = {"ca": ca_file}

engine = create_engine(
    os.getenv("DATABASE_URL"),
    connect_args=connect_args,
    pool_pre_ping=True,
)

def ensure_columns():
      """Add columns introduced after the first deploy (create_all never alters tables)."""
      cols = {c["name"] for c in inspect(engine).get_columns("positions")}
      if "nav_status" not in cols:
          with engine.begin() as conn:
              conn.execute(text("ALTER TABLE positions ADD COLUMN nav_status INT NULL"))