from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {
        "message": "SmartMail Router backend is running"
    }