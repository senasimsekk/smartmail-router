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

            expected_result = {
                "category": email.get("expected_category"),
                "department": email.get("expected_department"),
                "priority": email.get("expected_priority"),
                "requires_human_review": email.get("requires_human_review")
            }
            evaluation = {
                "category_correct": classification["category"] == expected_result["category"],
                "department_correct": classification["department"] == expected_result["department"],
                "priority_correct": classification["priority"] == expected_result["priority"],
                "requires_human_review_correct": classification["requires_human_review"] == expected_result["requires_human_review"]
            }

            all_correct = all(evaluation.values())
            return {
                "email_id": email_id,
                "subject": email.get("subject", ""),
                "sender": email.get("sender", ""),
                "classification": classification,
                "expected_result": expected_result,
                "evaluation": evaluation,
                "all_correct": all_correct
            }
    raise HTTPException(status_code=404, detail="Email not found")