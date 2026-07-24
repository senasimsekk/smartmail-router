from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import  Optional
from time import monotonic
from app.database import get_db
from collections import Counter
from app.services.email_ingestion_service import (
    create_email_from_manual_import,
    sync_mailbox_from_connector,
)
from app.services.response_suggestion_service import suggest_email_response
from app.services.ai_service import analyze_email_with_mock_ai
from app.services.classification_service import classify_email
from app.services.classification_db_service import save_classification_result
from app.services.email_analysis_service import analyze_email
from app.services.information_extraction_service import extract_structured_information
from app.services.evaluation_service import evaluate_classification
from app.services.evaluation_report_service import get_evaluation_report
from app.services.preprocessing_service import preprocess_email
from app.services.email_processing_service import process_email_by_id
from app.services.dashboard_service import (
    get_operational_dashboard_summary,
    get_operational_report,
)
from app.services.integration_service import (
    build_integration_overview,
    test_integration_connection,
)
from app.services.pipeline_service import build_email_pipeline
from app.services.notification_service import build_sla_notifications
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
from app.services.ticket_service import (
    TICKET_STATUSES,
    create_or_update_ticket_for_email,
    get_ticket_by_email_id,
    ticket_to_dict,
    update_ticket,
)


router = APIRouter(
    prefix="/emails",
    tags=["Emails"]
)

AI_ANALYSIS_CACHE_TTL_SECONDS = 600
AI_ANALYSIS_CACHE: dict[int, tuple[float, dict]] = {}


def get_cached_ai_analysis(email_id: int) -> dict | None:
    cached = AI_ANALYSIS_CACHE.get(email_id)

    if not cached:
        return None

    cached_at, cached_result = cached

    if monotonic() - cached_at > AI_ANALYSIS_CACHE_TTL_SECONDS:
        AI_ANALYSIS_CACHE.pop(email_id, None)
        return None

    return cached_result


def set_cached_ai_analysis(email_id: int, result: dict) -> None:
    AI_ANALYSIS_CACHE[email_id] = (monotonic(), result)


class ManualEmailImportRequest(BaseModel):
    subject: str
    sender: str
    body: str
    source_mailbox: Optional[str] = "webmaster@rekabet.gov.tr"
    has_attachment:bool = False
    attachment_names: list[str] = Field(default_factory=list)
    actor_role: str = "operator"


class MailboxSyncRequest(BaseModel):
    connector_id: str = "synthetic_demo"
    source_mailbox: str = "webmaster@rekabet.gov.tr"
    limit: int = Field(default=5, ge=1, le=50)
    actor_role: str = "operator"
    process_after_import: bool = True


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


class IntegrationTestRequest(BaseModel):
    actor_role: str = "operator"


class UpdateTicketRequest(BaseModel):
    status: Optional[str] = None
    responsible_person: Optional[str] = None
    note: Optional[str] = None
    response_text: Optional[str] = None
    closure_reason: Optional[str] = None
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
        email["classification"] = classification
        email["sla"] = calculate_sla(email, classification)
        emails.append(email)

    return {
        "count": len(emails),
        "emails": emails
    }
@router.get("/ingestion/overview")
def get_ingestion_overview(db: Session = Depends(get_db)):
    return get_email_ingestion_overview(db)


@router.get("/notifications/sla")
def get_sla_notifications(db: Session = Depends(get_db)):
    email_records = get_all_emails_from_db(db)
    return build_sla_notifications(email_records)


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

    cached_result = get_cached_ai_analysis(email_id)

    if cached_result:
        return {
            **cached_result,
            "cached": True,
        }

    email = email_to_dict(email_record)
    classification = classify_email(email)

    ai_analysis = analyze_email_with_mock_ai(
        email=email,
        rule_classification=classification,
    )

    result = {
        "email_id": email["id"],
        "subject": email["subject"],
        "sender": email["sender"],
        "ai_analysis": ai_analysis,
        "cached": False,
    }

    set_cached_ai_analysis(email_id, result)

    return result
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


@router.get("/{email_id:int}/pipeline")
def get_email_pipeline(email_id: int, db: Session = Depends(get_db)):
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")

    email = email_to_dict(email_record)
    classification = classify_email(email)
    analysis = analyze_email(email, classification)
    preprocessing = preprocess_email(email)
    logs = get_system_logs_by_email_id(db, email_id=email_id)
    ticket_record = get_ticket_by_email_id(db, email_id)
    ticket = ticket_to_dict(ticket_record) if ticket_record else None

    return {
        "email_id": email["id"],
        "subject": email["subject"],
        "pipeline": build_email_pipeline(
            email=email,
            classification=classification,
            analysis=analysis,
            preprocessing=preprocessing,
            logs=logs,
            ticket=ticket,
        ),
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


@router.get("/tickets/statuses")
def get_ticket_statuses():
    return {
        "statuses": TICKET_STATUSES,
    }


@router.get("/{email_id:int}/ticket")
def get_email_ticket(email_id: int, db: Session = Depends(get_db)):
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")

    try:
        ticket = get_ticket_by_email_id(db, email_id)
    except SQLAlchemyError:
        db.rollback()
        ticket = None

    return {
        "email_id": email_id,
        "ticket": ticket_to_dict(ticket) if ticket else None,
    }


@router.post("/{email_id:int}/ticket")
def create_email_ticket(
    email_id: int,
    request: UpdateTicketRequest,
    db: Session = Depends(get_db),
):
    require_permission(request.actor_role, "route_email")
    email_record = get_email_by_id_from_db(db, email_id)

    if email_record is None:
        raise HTTPException(status_code=404, detail="Email not found")

    try:
        ticket = create_or_update_ticket_for_email(
            db=db,
            email_record=email_record,
            created_by=request.actor_role,
        )
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Evrak/talep kaydı tablosu hazır değil. Lütfen veritabanı tablolarını güncelleyin.",
        ) from error

    return {
        "email_id": email_id,
        "ticket": ticket,
    }


@router.patch("/tickets/{ticket_id:int}")
def update_email_ticket(
    ticket_id: int,
    request: UpdateTicketRequest,
    db: Session = Depends(get_db),
):
    require_permission(request.actor_role, "route_email")

    try:
        ticket = update_ticket(
            db=db,
            ticket_id=ticket_id,
            status=request.status,
            responsible_person=request.responsible_person,
            note=request.note,
            response_text=request.response_text,
            closure_reason=request.closure_reason,
            actor=request.actor_role,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Evrak/talep kaydı tablosu hazır değil. Lütfen veritabanı tablolarını güncelleyin.",
        ) from error

    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return {
        "ticket": ticket,
    }


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


@router.post("/ingestion/sync")
def sync_mailbox(
    request: MailboxSyncRequest,
    db: Session = Depends(get_db),
):
    require_permission(request.actor_role, "import_email")

    try:
        return sync_mailbox_from_connector(
            db=db,
            connector_id=request.connector_id,
            source_mailbox=request.source_mailbox,
            limit=request.limit,
            process_after_import=request.process_after_import,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except ConnectionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except (NotImplementedError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


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


@router.get("/evaluation/report")
def get_model_evaluation_report(db: Session = Depends(get_db)):
    return get_evaluation_report(db)


@router.get("/reports/management")
def get_management_report(db: Session = Depends(get_db)):
    return get_operational_report(db)


@router.get("/integrations/overview")
def get_integration_overview(db: Session = Depends(get_db)):
    return build_integration_overview(db)


@router.post("/integrations/{integration_id}/test")
def test_integration(
    integration_id: str,
    payload: IntegrationTestRequest,
    db: Session = Depends(get_db),
):
    try:
        return test_integration_connection(
            db,
            integration_id=integration_id,
            actor_role=payload.actor_role,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


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
    email = email_to_dict(email_record)
    preprocessing_result = preprocess_email(email)

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
