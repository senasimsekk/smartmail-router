from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.classification_service import classify_email
from app.services.evaluation_service import evaluate_classification
from app.services.preprocessing_service import preprocess_email
from app.services.email_db_service import (
    email_to_dict,
    get_all_emails_from_db,
    get_email_by_id_from_db
    
)


router = APIRouter(
    prefix="/emails",
    tags=["Emails"]
)


@router.get("")
def get_emails(db: Session = Depends(get_db)):
    email_records = get_all_emails_from_db(db)
    emails = [email_to_dict(email) for email in email_records]

    return {
        "count": len(emails),
        "emails": emails
    }


@router.get("/{email_id}")
def get_email_by_id(email_id: int, db: Session = Depends(get_db)):
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return email_to_dict(email_record)

    
@router.get("/{email_id}/preprocess")
def preprocess_email_by_id(email_id: int, db: Session = Depends(get_db)):
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")
    email=email_to_dict(email_record)
    preprocessing_result = preprocess_email(email_to_dict(email))

    return {
                "email_id": email["id"],
                "sender": email["sender"],
                "preprocessing": preprocessing_result,
            }

 

@router.post("/{email_id}/classify")
def classify_email_by_id(email_id: int, db: Session = Depends(get_db)):
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")

    email = email_to_dict(email_record)
    classification = classify_email(email)
    evaluation_result = evaluate_classification(email, classification)

    return {
         "email_id": email["id"],
         "subject": email["subject"],
         "sender": email["sender"],
         "classification": classification,
         "expected_result": evaluation_result["expected_result"],
         "evaluation": evaluation_result["evaluation"],
         "all_correct": evaluation_result["all_correct"],
     }

  


@router.post("/classify-all")
def classify_all_emails(db: Session = Depends(get_db)):
    email_records = get_all_emails_from_db(db)
    emails = [email_to_dict(email) for email in email_records]

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
            "all_correct": evaluation_result["all_correct"],
        })

    total_emails = len(emails)
    accuracy = correct_count / total_emails if total_emails > 0 else 0

    return {
        "total_emails": total_emails,
        "correct_predictions": correct_count,
        "wrong_predictions": total_emails - correct_count,
        "accuracy": round(accuracy, 2),
        "results": results,
    }


@router.post("/classify-errors")
def classify_errors(db: Session = Depends(get_db)):
    email_records = get_all_emails_from_db(db)
    emails = [email_to_dict(email) for email in email_records]

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
                "evaluation": evaluation_result["evaluation"],
            })

    return {
        "error_count": len(errors),
        "errors": errors,
    }