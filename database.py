import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

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