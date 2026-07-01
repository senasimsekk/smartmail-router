from fastapi import FastAPI

from app.routers import emails


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