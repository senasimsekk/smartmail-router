from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from collections import Counter
from app.services.ai_service import analyze_email_with_mock_ai
from app.services.classification_service import classify_email
from app.services.email_analysis_service import analyze_email
from app.services.information_extraction_service import extract_structured_information
from app.services.evaluation_service import evaluate_classification
from app.services.preprocessing_service import preprocess_email
from app.services.email_db_service import (
    email_to_dict,
    get_all_emails_from_db,
    get_email_by_id_from_db,
    get_email_ingestion_overview,
    get_emails_by_source_mailbox,
    get_mailbox_statistics
    
)
from app.services.classification_db_service import (
    classification_record_to_dict,
    save_classification_result,
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
@router.get("/ingestion/overview")
def get_ingestion_overview(db: Session = Depends(get_db)):
    return get_email_ingestion_overview(db)
@router.get("/ingestion/mailboxes")
def get_ingestion_mailboxes(db: Session = Depends(get_db)):
    return {
        "mailbox_statistics": get_mailbox_statistics(db),
    }


@router.get("/ingestion/mailboxes/{mailbox}/emails")
def get_emails_from_mailbox(
    mailbox: str,
    db: Session = Depends(get_db),
):
    emails = get_emails_by_source_mailbox(db, mailbox)

    return {
        "mailbox": mailbox,
        "email_count": len(emails),
        "emails": emails,
    }
@router.get("/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    email_records = get_all_emails_from_db(db)
    emails = [email_to_dict(email) for email in email_records]

    category_counter = Counter()
    department_counter = Counter()
    priority_counter = Counter()
    source_mailbox_counter = Counter()
    operation_type_counter = Counter()
    risk_level_counter = Counter()

    total_emails = len(emails)
    correct_predictions = 0
    human_review_count = 0
    critical_risk_count = 0
    attachment_email_count = 0
    needs_response_count = 0

    for email in emails:
        classification = classify_email(email)
        evaluation_result = evaluate_classification(email, classification)
        analysis = analyze_email(email, classification)

        category_counter[classification["category"]] += 1
        department_counter[classification["department"]] += 1
        priority_counter[classification["priority"]] += 1
        source_mailbox_counter[email.get("source_mailbox") or "unknown"] += 1
        operation_type_counter[analysis["operation_type"]] += 1
        risk_level_counter[analysis["risk_level"]] += 1

        if evaluation_result["all_correct"]:
            correct_predictions += 1

        if classification.get("requires_human_review"):
            human_review_count += 1

        if analysis["risk_level"] == "Kritik":
            critical_risk_count += 1

        if email.get("has_attachment"):
            attachment_email_count += 1

        if analysis["needs_response"]:
            needs_response_count += 1

    accuracy = correct_predictions / total_emails if total_emails > 0 else 0

    return {
        "total_emails": total_emails,
        "correct_predictions": correct_predictions,
        "wrong_predictions": total_emails - correct_predictions,
        "accuracy": round(accuracy, 2),
        "human_review_count": human_review_count,
        "critical_risk_count": critical_risk_count,
        "attachment_email_count": attachment_email_count,
        "needs_response_count": needs_response_count,
        "category_distribution": dict(category_counter),
        "department_distribution": dict(department_counter),
        "priority_distribution": dict(priority_counter),
        "source_mailbox_distribution": dict(source_mailbox_counter),
        "operation_type_distribution": dict(operation_type_counter),
        "risk_level_distribution": dict(risk_level_counter),
    }
@router.get("/{email_id}/ai-analysis")
def get_email_ai_analysis(email_id: int, db: Session = Depends(get_db)):
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")

    email = email_to_dict(email_record)
    classification = classify_email(email)

    ai_analysis = analyze_email_with_mock_ai(
        email=email,
        rule_classification=classification,
    )

    return {
        "email_id": email["id"],
        "subject": email["subject"],
        "sender": email["sender"],
        "ai_analysis": ai_analysis,
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

    saved_classification = save_classification_result(
        db=db,
        email_id=email_id,
        classification=classification,
        evaluation_result=evaluation_result,
    )

    return {
         "email_id": email["id"],
         "subject": email["subject"],
         "sender": email["sender"],
         "classification": classification,
         "expected_result": evaluation_result["expected_result"],
         "evaluation": evaluation_result["evaluation"],
         "all_correct": evaluation_result["all_correct"],
         "saved_classification": classification_record_to_dict(saved_classification),
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
@router.get("/{email_id}/analysis")
def analyze_email_by_id(email_id: int, db: Session = Depends(get_db)):
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")

    email = email_to_dict(email_record)

    classification = classify_email(email)
    analysis = analyze_email(email, classification)
    extracted_information = extract_structured_information(email, classification)

    return {
        "email_id": email["id"],
        "subject": email["subject"],
        "sender": email["sender"],
        "classification": classification,
        "analysis": analysis,
        "extracted_information": extracted_information,
    }       