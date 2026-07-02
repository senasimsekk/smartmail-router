from fastapi import FastAPI
from sqlalchemy import text

from app.routers import emails
from app.database import engine

app = FastAPI(
    title="SmartMail Router API",
    description="AI-assisted institutional email classification and routing system.",
    version="0.1.0"
)


app.include_router(emails.router)


@app.get("/")
def home():
    return {
        "message": "SmartMail Router backend is running"
    }

@app.get("/db-test")
def test_database_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        db_version = result.fetchone()[0]

    return {
        "database_status": "connected",
        "postgres_version": db_version
    }