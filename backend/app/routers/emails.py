from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import  Optional
from app.database import get_db
from collections import Counter
from app.services.email_ingestion_service import create_email_from_manual_import
from app.services.response_suggestion_service import suggest_email_response
from app.services.ai_service import analyze_email_with_mock_ai
from app.services.classification_service import classify_email
from app.services.classification_db_service import save_classification_result
from app.services.email_analysis_service import analyze_email
from app.services.information_extraction_service import extract_structured_information
from app.services.evaluation_service import evaluate_classification
from app.services.preprocessing_service import preprocess_email
from app.services.email_processing_service import process_email_by_id
from app.services.dashboard_service import get_operational_dashboard_summary
from app.services.attachment_text_extraction_service import (
    save_attachment_and_extract_text,
)
from app.services.authorization_service import (
    get_available_roles,
    role_has_permission,
)
from app.services.sla_service import calculate_sla
from app.services.trainable_model_service import (
    ModelDependencyError,
    ModelNotTrainedError,
    get_model_status,
    predict_email_with_trained_model,
    train_email_classifier,
)
from app.services.email_db_service import (
    email_to_dict,
    get_all_emails_from_db,
    get_email_by_id_from_db,
    get_email_ingestion_overview,
    get_emails_by_source_mailbox,
    get_mailbox_statistics
    
)
from app.services.routing_service import (
    get_pending_review_emails,
      approve_email_routing,
      correct_email_routing,
      route_email_to_department
)
from app.services.classification_db_service import (
    classification_record_to_dict,
    save_classification_result,
)
from app.services.feedback_service import (
    create_feedback,
    create_training_example_from_feedback,
    feedback_to_dict,
    get_all_feedbacks,
    get_feedbacks_by_email_id,
)
from app.services.system_log_service import (
    create_system_log,
    get_all_system_logs,
    get_system_logs_by_email_id,
)


router = APIRouter(
    prefix="/emails",
    tags=["Emails"]
)
class ManualEmailImportRequest(BaseModel):
    subject: str
    sender: str
    body: str
    source_mailbox: Optional[str] = "webmaster@rekabet.gov.tr"
    has_attachment:bool = False
    attachment_names: list[str] = Field(default_factory=list)
    actor_role: str = "operator"
class ApproveRoutingRequest(BaseModel):
    approved_by: str
    actor_role: str = "operator"
    approved_department: Optional[str] = None
    routing_note: Optional[str] = None


class CorrectRoutingRequest(BaseModel):
    corrected_category: str
    corrected_department: str
    corrected_priority: str
    corrected_by: str
    actor_role: str = "operator"
    feedback_note: Optional[str] = None

class RouteEmailRequest(BaseModel):
    routed_by: str
    actor_role: str = "operator"
    target_department: Optional[str] = None
    routing_note: Optional[str] = None


class TrainModelRequest(BaseModel):
    actor_role: str = "operator"


def require_permission(actor_role: str, permission: str):
    if not role_has_permission(actor_role, permission):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{actor_role}' is not allowed to perform '{permission}'.",
        )


@router.get("/auth/roles")
def get_roles():
    return {
        "roles": get_available_roles(),
    }


@router.post("/{email_id:int}/attachments/upload")
async def upload_email_attachment(
    email_id: int,
    file: UploadFile = File(...),
    uploaded_by: str = Form("operator"),
    actor_role: str = Form("operator"),
    db: Session = Depends(get_db),
):
    require_permission(actor_role, "upload_attachment")

    file_content = await file.read()

    result = save_attachment_and_extract_text(
        db=db,
        email_id=email_id,
        filename=file.filename or "attachment",
        file_content=file_content,
        uploaded_by=uploaded_by,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Email not found")

    return result


@router.post("/{email_id:int}/route")
def route_email(
    request: RouteEmailRequest,
    email_id: int,
    db: Session = Depends(get_db)
):
    require_permission(request.actor_role, "route_email")

    result = route_email_to_department(
        db=db,
        email_id=email_id,
        routed_by=request.routed_by,
        target_department=request.target_department,
        routing_note=request.routing_note,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Email not found")

    return result

@router.get("")
def get_emails(db: Session = Depends(get_db)):
    email_records = get_all_emails_from_db(db)
    emails = []

    for email_record in email_records:
        email = email_to_dict(email_record)
        classification = classify_email(email)
        email["sla"] = calculate_sla(email, classification)
        emails.append(email)

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
    sla_status_counter = Counter()

    total_emails = len(emails)
    correct_predictions = 0
    human_review_count = 0
    critical_risk_count = 0
    attachment_email_count = 0
    needs_response_count = 0
    sla_due_soon_count = 0
    sla_overdue_count = 0

    for email in emails:
        classification = classify_email(email)
        evaluation_result = evaluate_classification(email, classification)
        analysis = analyze_email(email, classification)
        sla = analysis["sla"]

        category_counter[classification["category"]] += 1
        department_counter[classification["department"]] += 1
        priority_counter[classification["priority"]] += 1
        source_mailbox_counter[email.get("source_mailbox") or "unknown"] += 1
        operation_type_counter[analysis["operation_type"]] += 1
        risk_level_counter[analysis["risk_level"]] += 1
        sla_status_counter[sla["status_label"]] += 1

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

        if sla["status"] == "Due soon":
            sla_due_soon_count += 1

        if sla["status"] == "Overdue":
            sla_overdue_count += 1

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
        "sla_due_soon_count": sla_due_soon_count,
        "sla_overdue_count": sla_overdue_count,
        "category_distribution": dict(category_counter),
        "department_distribution": dict(department_counter),
        "priority_distribution": dict(priority_counter),
        "source_mailbox_distribution": dict(source_mailbox_counter),
        "operation_type_distribution": dict(operation_type_counter),
        "risk_level_distribution": dict(risk_level_counter),
        "sla_status_distribution": dict(sla_status_counter),
    }
@router.get("/{email_id:int}/ai-analysis")
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
@router.get("/{email_id:int}/response-suggestion")
def get_response_suggestion(email_id: int, db: Session = Depends(get_db)):
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")

    email = email_to_dict(email_record)

    classification = classify_email(email)
    analysis = analyze_email(email, classification)
    extracted_information = extract_structured_information(email, classification)

    response_suggestion = suggest_email_response(
        email=email,
        classification=classification,
        analysis=analysis,
        extracted_information=extracted_information,
    )

    return {
        "email_id": email["id"],
        "subject": email["subject"],
        "sender": email["sender"],
        "category": classification["category"],
        "department": classification["department"],
        "priority": classification["priority"],
        "risk_level": analysis["risk_level"],
        "operation_type": analysis["operation_type"],
        "response_suggestion": response_suggestion,
    }
@router.post("/{email_id:int}/feedback")
def add_feedback_for_email(
    email_id: int,
    corrected_category: str,
    corrected_department: str,
    corrected_priority: str,
    actor_role: str = "operator",
    feedback_note: str | None = None,
    created_by: str | None = None,
    db: Session = Depends(get_db),
):
    require_permission(actor_role, "create_feedback")

    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")

    email = email_to_dict(email_record)
    original_classification = classify_email(email)

    feedback = create_feedback(
        db=db,
        email_id=email_id,
        original_classification=original_classification,
        corrected_category=corrected_category,
        corrected_department=corrected_department,
        corrected_priority=corrected_priority,
        feedback_note=feedback_note,
        created_by=created_by,
    )

    return {
        "message": "Feedback saved successfully.",
        "email_id": email_id,
        "original_classification": original_classification,
        "feedback": feedback_to_dict(feedback),
    }


@router.get("/{email_id:int}/feedback")
def get_email_feedbacks(email_id: int, db: Session = Depends(get_db)):
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")

    feedbacks = get_feedbacks_by_email_id(db, email_id)

    return {
        "email_id": email_id,
        "feedback_count": len(feedbacks),
        "feedbacks": [
            feedback_to_dict(feedback)
            for feedback in feedbacks
        ],
    }


@router.get("/feedback/all")
def get_feedbacks(db: Session = Depends(get_db)):
    feedbacks = get_all_feedbacks(db)

    return {
        "feedback_count": len(feedbacks),
        "feedbacks": [
            feedback_to_dict(feedback)
            for feedback in feedbacks
        ],
    }


@router.get("/feedback/training-data")
def get_feedback_training_data(db: Session = Depends(get_db)):
    feedbacks = get_all_feedbacks(db)

    training_examples = []

    for feedback in feedbacks:
        email_record = get_email_by_id_from_db(db, feedback.email_id)

        if email_record is None:
            continue

        email = email_to_dict(email_record)

        training_examples.append(
            create_training_example_from_feedback(
                feedback=feedback,
                email=email,
            )
        )

    return {
        "training_example_count": len(training_examples),
        "training_examples": training_examples,
    }


@router.get("/model/status")
def get_trainable_model_status():
    try:
        return get_model_status()
    except ModelDependencyError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/model/train")
def train_model(
    request: TrainModelRequest,
    db: Session = Depends(get_db),
):
    require_permission(request.actor_role, "view_training_data")

    try:
        result = train_email_classifier(db)
    except ModelDependencyError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    create_system_log(
        db=db,
        action_type="MODEL_TRAINED",
        action_detail="Trainable email classifier was trained.",
        actor=request.actor_role,
        extra_data=result["metadata"],
    )

    return result
@router.get("/review/pending")
def get_pending_review_email_list(db: Session = Depends(get_db)):
    pending_emails = get_pending_review_emails(db)

    return {
        "count": len(pending_emails),
        "pending_emails": pending_emails,
    }


@router.post("/{email_id:int}/approve-routing")
def approve_routing(
    email_id: int,
    request: ApproveRoutingRequest,
    db: Session = Depends(get_db),
):
    require_permission(request.actor_role, "approve_routing")

    result = approve_email_routing(
        db=db,
        email_id=email_id,
        approved_by=request.approved_by,
        approved_department=request.approved_department,
        routing_note=request.routing_note,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Email not found")

    return result

@router.post("/{email_id:int}/correct-routing")
def correct_routing(
    email_id: int,
    request: CorrectRoutingRequest,
    db: Session = Depends(get_db),
):
    require_permission(request.actor_role, "correct_routing")

    result = correct_email_routing(
        db=db,
        email_id=email_id,
        corrected_category=request.corrected_category,
        corrected_department=request.corrected_department,
        corrected_priority=request.corrected_priority,
        corrected_by=request.corrected_by,
        feedback_note=request.feedback_note,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Email not found")

    return result
@router.post("/ingestion/manual-import")
def manual_email_import(
    request: ManualEmailImportRequest,
    db: Session = Depends(get_db),
):
    require_permission(request.actor_role, "import_email")

    created_email = create_email_from_manual_import(
        db=db,
        subject=request.subject,
        sender=request.sender,
        body=request.body,
        source_mailbox=request.source_mailbox,
        has_attachment=request.has_attachment,
        attachment_names=request.attachment_names,
    )

    processed_email = process_email_by_id(
        db=db,
        email_id=created_email["id"],
    )
    return {
        "message": "Email was imported and processed successfully.",
        "imported_email": created_email,
        "processing_result": processed_email,
    }

@router.post("/{email_id:int}/process")
def process_email(
    email_id: int,
    actor_role: str = "operator",
    db: Session = Depends(get_db),
):
    require_permission(actor_role, "process_email")

    result = process_email_by_id(
        db=db,
        email_id=email_id,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Email not found")

    return result

@router.get("/logs/all")
def get_system_log_list(
    limit: int = 100,
    db: Session = Depends(get_db),
):
    logs = get_all_system_logs(db, limit=limit)

    return {
        "count": len(logs),
        "logs": logs,
    }


@router.get("/{email_id:int}/logs")
def get_email_system_logs(
    email_id: int,
    db: Session = Depends(get_db),
):
    logs = get_system_logs_by_email_id(db, email_id=email_id)

    return {
        "email_id": email_id,
        "count": len(logs),
        "logs": logs,
    }


@router.get("/{email_id:int}/model-prediction")
def get_model_prediction(
    email_id: int,
    db: Session = Depends(get_db),
):
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")

    email = email_to_dict(email_record)

    try:
        prediction = predict_email_with_trained_model(email)
    except ModelDependencyError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except ModelNotTrainedError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return {
        "email_id": email["id"],
        "subject": email["subject"],
        "model_prediction": prediction,
    }
@router.get("/dashboard/operational")
def get_operational_dashboard(
    db: Session = Depends(get_db),
):
    return get_operational_dashboard_summary(db)

@router.get("/{email_id:int}")
def get_email_by_id(email_id: int, db: Session = Depends(get_db)):
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return email_to_dict(email_record)

    
@router.get("/{email_id:int}/preprocess")
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

 

@router.post("/{email_id:int}/classify")
def classify_email_by_id(
    email_id: int,
    actor_role: str = "operator",
    db: Session = Depends(get_db),
):
    require_permission(actor_role, "process_email")

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
@router.get("/{email_id:int}/analysis")
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
