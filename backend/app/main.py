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
    
def evaluate_classification(email: dict, classification: dict) -> dict:
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
    "expected_result": expected_result,
    "evaluation": evaluation,
    "all_correct": all_correct
}

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
            evaluation_result=evaluate_classification(email, classification)
            return {
                "email_id": email_id,
                "subject": email.get("subject", ""),
                "sender": email.get("sender", ""),
                "classification": classification,
                "evaluation": evaluation_result["evaluation"],
                "all_correct": evaluation_result["all_correct"]
            }
    raise HTTPException(status_code=404, detail="Email not found")
           
@app.post("/emails/classify-all")
def classify_all_emails():
    emails = load_emails()

    results = []
    correct_count = 0

    for email in emails:
        classification = classify_email(email)
        evaluation_result = evaluate_classification(email, classification)

        if evaluation_result["all_correct"]:
            correct_count += 1

        results.append({
            "email_id": email["id"],
            "subject": email["subject"],
            "sender": email["sender"],
            "classification": classification,
            "expected_result": evaluation_result["expected_result"],
            "evaluation": evaluation_result["evaluation"],
            "all_correct": evaluation_result["all_correct"]
        })

    total_emails = len(emails)
    accuracy = correct_count / total_emails if total_emails > 0 else 0

    return {
        "total_emails": total_emails,
        "correct_predictions": correct_count,
        "wrong_predictions": total_emails - correct_count,
        "accuracy": round(accuracy, 2),
        "results": results
    }
@app.post("/emails/classify-errors")
def classify_errors():
    emails = load_emails()

    errors = []

    for email in emails:
        classification = classify_email(email)
        evaluation_result = evaluate_classification(email, classification)

        if not evaluation_result["all_correct"]:
            errors.append({
                "email_id": email["id"],
                "subject": email["subject"],
                "sender": email["sender"],
                "classification": classification,
                "expected_result": evaluation_result["expected_result"],
                "evaluation": evaluation_result["evaluation"]
            })

    return {
        "error_count": len(errors),
        "errors": errors
    }    
        