from fastapi import FastAPI, HTTPException
from pathlib import Path
from app.services.classification_service import classify_email
import json

app=FastAPI(
title="SmartMail Router API",
description="AI-assisted email routing based on their content.",
version="0.1.0"
)

BASE_DIR= Path(__file__).resolve().parents[2]
DATA_FILE= BASE_DIR / "data" / "synthetic_emails.json"

def load_emails():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {DATA_FILE}")
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

@app.get("/")
def home():
    return {
        "message": "SmartMail Router backend is running"
    }
    
@app.get("/emails")
def get_emails():
    emails=load_emails()
    return {
        "count": len(emails),
        "emails": emails
    }

@app.get("/emails/{email_id}")
def get_email_by_id(email_id: int):
    emails=load_emails()
    
    for email in emails:
        if email["id"] == email_id:
            return email
    raise HTTPException(status_code=404, detail="Email not found")

@app.post("/email/{email_id}/classify")
def classify_email_endpoint(email_id: int):
    emails=load_emails()
    
    for email in emails:
        if email["id"] == email_id:
            classification=classify_email(email)
            return {
                "email_id": email_id,
                "subject": email.get("subject", ""),
                "sender": email.get("sender", ""),
                "classification": classification
            }
    raise HTTPException(status_code=404, detail="Email not found")