from fastapi import APIRouter, HTTPException

from app.services.email_data_service import load_emails
from app.services.classification_service import classify_email
from app.services.evaluation_service import evaluate_classification
from app.services.preprocessing_service import preprocess_email


router = APIRouter(
    prefix="/emails",
    tags=["Emails"]
)


@router.get("")
def get_emails():
    emails = load_emails()

    return {
        "count": len(emails),
        "emails": emails
    }


@router.get("/{email_id}")
def get_email_by_id(email_id: int):
    emails = load_emails()

    for email in emails:
        if email["id"] == email_id:
            return email

    raise HTTPException(status_code=404, detail="Email not found")
@router.get("/{email_id}/preprocess")
def preprocess_email_by_id(email_id: int):
    emails = load_emails()

    for email in emails:
        if email["id"] == email_id:
            preprocessing_result = preprocess_email(email)

            return {
                "email_id": email["id"],
                "sender": email["sender"],
                "preprocessing": preprocessing_result,
            }

    raise HTTPException(status_code=404, detail="Email not found")

@router.post("/{email_id}/classify")
def classify_email_by_id(email_id: int):
    emails = load_emails()

    for email in emails:
        if email["id"] == email_id:
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

    raise HTTPException(status_code=404, detail="Email not found")


@router.post("/classify-all")
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
                "evaluation": evaluation_result["evaluation"],
            })

    return {
        "error_count": len(errors),
        "errors": errors,
    }