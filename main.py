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
    
