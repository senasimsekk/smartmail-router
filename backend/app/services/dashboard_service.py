from collections import Counter
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.email import Email
from app.models.system_log import SystemLog
from app.services.classification_service import classify_email
from app.services.email_db_service import email_to_dict
from app.services.email_analysis_service import analyze_email
from app.services.evaluation_service import evaluate_classification
from app.services.sla_service import calculate_sla
from app.services.system_log_service import system_log_to_dict


def calculate_rate(part: int, total: int) -> float:
    if total == 0:
        return 0

    return round(part / total, 2)


def parse_datetime_value(value) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def average(values: list[float]) -> float | None:
    if not values:
        return None

    return round(sum(values) / len(values), 2)


def group_logs_by_email(logs: list[dict]) -> dict[int, list[dict]]:
    grouped_logs = {}

    for log in logs:
        email_id = log.get("email_id")

        if email_id is None:
            continue

        grouped_logs.setdefault(email_id, []).append(log)

    return grouped_logs


def get_first_log_at(logs: list[dict], action_types: set[str]) -> datetime | None:
    timestamps = [
        parse_datetime_value(log.get("created_at"))
        for log in logs
        if log.get("action_type") in action_types
    ]
    timestamps = [timestamp for timestamp in timestamps if timestamp is not None]

    if not timestamps:
        return None

    return min(timestamps)


def get_first_closure_log_at(logs: list[dict]) -> datetime | None:
    timestamps = []

    for log in logs:
        extra_data = log.get("extra_data") or {}
        status = extra_data.get("status")
        is_closure_log = (
            log.get("action_type") == "TICKET_UPDATED"
            and status in {"Tamamlandı", "Arşivlendi"}
        )

        if is_closure_log:
            timestamp = parse_datetime_value(log.get("created_at"))

            if timestamp is not None:
                timestamps.append(timestamp)

    if not timestamps:
        return None

    return min(timestamps)


def is_spam_or_automatic_email(email: dict, analysis: dict) -> bool:
    normalized_text = " ".join(
        [
            email.get("subject") or "",
            email.get("sender") or "",
            email.get("body") or "",
        ]
    ).lower()

    spam_keywords = [
        "spam",
        "reklam",
        "kampanya",
        "unsubscribe",
        "no-reply",
        "noreply",
        "otomatik cevap",
        "auto reply",
    ]

    return (
        analysis.get("operation_type") == "Reddedilebilir/spam olabilir"
        or any(keyword in normalized_text for keyword in spam_keywords)
    )


def build_report_action_items(
    overdue_count: int,
    pending_review_count: int,
    critical_risk_count: int,
    attachment_email_count: int,
    needs_response_count: int,
) -> list[dict]:
    action_items = [
        {
            "label": "Geciken süre hedefi",
            "count": overdue_count,
            "tone": "danger",
            "recommendation": "SLA süresi geçen kayıtlar öncelikli incelenmeli.",
        },
        {
            "label": "İnsan onayı bekleyen",
            "count": pending_review_count,
            "tone": "warning",
            "recommendation": "Operatör onayı bekleyen e-postalar sıraya alınmalı.",
        },
        {
            "label": "Kritik risk",
            "count": critical_risk_count,
            "tone": "danger",
            "recommendation": "Kritik riskli kayıtlar ilgili birim amirine görünür olmalı.",
        },
        {
            "label": "Ek dosyalı kayıt",
            "count": attachment_email_count,
            "tone": "warning",
            "recommendation": "Eklerde OCR, güvenlik ve kişisel veri kontrolleri tamamlanmalı.",
        },
        {
            "label": "Cevap gerektiren",
            "count": needs_response_count,
            "tone": "neutral",
            "recommendation": "Cevap taslağı ve kapanış süreci takip edilmeli.",
        },
    ]

    return [
        item
        for item in action_items
        if item["count"] > 0
    ]


def build_operational_report(emails: list[dict], logs: list[dict] | None = None) -> dict:
    logs = logs or []
    logs_by_email = group_logs_by_email(logs)
    total_emails = len(emails)
    category_counter = Counter()
    department_counter = Counter()
    priority_counter = Counter()
    risk_level_counter = Counter()
    mailbox_rows = {}
    daily_rows = {}

    auto_routed_count = 0
    pending_review_count = 0
    critical_risk_count = 0
    attachment_email_count = 0
    needs_response_count = 0
    sla_due_soon_count = 0
    sla_overdue_count = 0
    wrong_routing_count = 0
    correct_prediction_count = 0
    operator_intervention_count = 0
    spam_or_automatic_count = 0
    today_email_count = 0
    classified_count = 0
    routing_duration_seconds = []
    closure_duration_seconds = []
    today = datetime.now(UTC).date().isoformat()

    for email in emails:
        classification = classify_email(email)
        evaluation_result = evaluate_classification(email, classification)
        analysis = analyze_email(email, classification)
        sla = analysis["sla"]
        source_mailbox = email.get("source_mailbox") or "unknown"
        routing_status = email.get("routing_status") or "New"
        created_date = (email.get("created_at") or "")[:10] or "Tarihsiz"
        created_at = parse_datetime_value(email.get("created_at"))
        email_logs = logs_by_email.get(email.get("id"), [])

        category_counter[classification["category"]] += 1
        department_counter[classification["department"]] += 1
        priority_counter[classification["priority"]] += 1
        risk_level_counter[analysis["risk_level"]] += 1

        is_auto_routed = routing_status == "Routed" and email.get("approved_by") == "system"
        is_pending_review = routing_status == "Pending Review"
        is_critical = analysis["risk_level"] == "Kritik"
        has_attachment = bool(email.get("has_attachment"))
        has_operator_intervention = any(
            log.get("actor") not in {"system", "mailbox_sync"}
            for log in email_logs
        )

        if created_date == today:
            today_email_count += 1

        if routing_status != "New":
            classified_count += 1

        if routing_status == "Corrected":
            wrong_routing_count += 1

        if evaluation_result["all_correct"]:
            correct_prediction_count += 1

        if has_operator_intervention:
            operator_intervention_count += 1

        if is_spam_or_automatic_email(email, analysis):
            spam_or_automatic_count += 1

        if is_auto_routed:
            auto_routed_count += 1

        if is_pending_review:
            pending_review_count += 1

        if is_critical:
            critical_risk_count += 1

        if has_attachment:
            attachment_email_count += 1

        if analysis["needs_response"]:
            needs_response_count += 1

        if sla["status"] == "Due soon":
            sla_due_soon_count += 1

        if sla["status"] == "Overdue":
            sla_overdue_count += 1

        routing_completed_at = (
            parse_datetime_value(email.get("approved_at"))
            or get_first_log_at(
                email_logs,
                {"EMAIL_ROUTED", "ROUTING_APPROVED", "ROUTING_CORRECTED"},
            )
        )
        closure_completed_at = get_first_closure_log_at(email_logs)

        if created_at is not None and routing_completed_at is not None:
            routing_duration_seconds.append(
                max((routing_completed_at - created_at).total_seconds(), 0)
            )

        if created_at is not None and closure_completed_at is not None:
            closure_duration_seconds.append(
                max((closure_completed_at - created_at).total_seconds(), 0)
            )

        mailbox = mailbox_rows.setdefault(
            source_mailbox,
            {
                "mailbox": source_mailbox,
                "total": 0,
                "auto_routed": 0,
                "pending_review": 0,
                "overdue": 0,
                "critical": 0,
                "with_attachment": 0,
                "spam_or_automatic": 0,
            },
        )
        mailbox["total"] += 1
        mailbox["auto_routed"] += int(is_auto_routed)
        mailbox["pending_review"] += int(is_pending_review)
        mailbox["overdue"] += int(sla["status"] == "Overdue")
        mailbox["critical"] += int(is_critical)
        mailbox["with_attachment"] += int(has_attachment)
        mailbox["spam_or_automatic"] += int(is_spam_or_automatic_email(email, analysis))

        daily = daily_rows.setdefault(
            created_date,
            {
                "date": created_date,
                "total": 0,
                "critical": 0,
                "pending_review": 0,
                "routed": 0,
                "spam_or_automatic": 0,
            },
        )
        daily["total"] += 1
        daily["critical"] += int(is_critical)
        daily["pending_review"] += int(is_pending_review)
        daily["routed"] += int(routing_status == "Routed")
        daily["spam_or_automatic"] += int(is_spam_or_automatic_email(email, analysis))

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "kpis": {
            "total_emails": total_emails,
            "today_email_count": today_email_count,
            "classified_count": classified_count,
            "auto_routed_count": auto_routed_count,
            "pending_review_count": pending_review_count,
            "critical_risk_count": critical_risk_count,
            "wrong_routing_count": wrong_routing_count,
            "attachment_email_count": attachment_email_count,
            "needs_response_count": needs_response_count,
            "sla_due_soon_count": sla_due_soon_count,
            "sla_overdue_count": sla_overdue_count,
            "spam_or_automatic_count": spam_or_automatic_count,
            "average_routing_seconds": average(routing_duration_seconds),
            "average_closure_seconds": average(closure_duration_seconds),
            "ai_accuracy_rate": calculate_rate(correct_prediction_count, total_emails),
            "auto_route_rate": calculate_rate(auto_routed_count, total_emails),
            "human_review_rate": calculate_rate(pending_review_count, total_emails),
            "wrong_routing_rate": calculate_rate(wrong_routing_count, total_emails),
            "operator_intervention_rate": calculate_rate(
                operator_intervention_count,
                total_emails,
            ),
            "attachment_rate": calculate_rate(attachment_email_count, total_emails),
            "sla_overdue_rate": calculate_rate(sla_overdue_count, total_emails),
            "spam_or_automatic_rate": calculate_rate(
                spam_or_automatic_count,
                total_emails,
            ),
        },
        "action_items": build_report_action_items(
            overdue_count=sla_overdue_count,
            pending_review_count=pending_review_count,
            critical_risk_count=critical_risk_count,
            attachment_email_count=attachment_email_count,
            needs_response_count=needs_response_count,
        ),
        "mailbox_performance": sorted(
            mailbox_rows.values(),
            key=lambda row: (-row["total"], row["mailbox"]),
        ),
        "daily_volume": sorted(daily_rows.values(), key=lambda row: row["date"])[-7:],
        "top_categories": category_counter.most_common(6),
        "top_departments": department_counter.most_common(6),
        "department_workload": dict(department_counter),
        "category_distribution": dict(category_counter),
        "priority_distribution": dict(priority_counter),
        "risk_distribution": dict(risk_level_counter),
    }


def get_operational_report(db: Session) -> dict:
    email_records = db.query(Email).order_by(Email.created_at).all()
    log_records = db.query(SystemLog).order_by(SystemLog.created_at).all()
    emails = [email_to_dict(email) for email in email_records]
    logs = [system_log_to_dict(log) for log in log_records]

    return build_operational_report(emails, logs)


def get_operational_dashboard_summary(db: Session) -> dict:
    emails = db.query(Email).all()
    logs = db.query(SystemLog).all()

    total_emails = len(emails)

    routing_status_distribution = Counter(
        email.routing_status or "Unknown" for email in emails
    )

    system_log_action_distribution = Counter(
        log.action_type for log in logs
    )

    pending_review_count = sum(
        1 for email in emails if email.routing_status == "Pending Review"
    )

    approved_count = sum(
        1 for email in emails if email.routing_status == "Approved"
    )

    corrected_count = sum(
        1 for email in emails if email.routing_status == "Corrected"
    )

    classified_count = sum(
        1 for email in emails if email.routing_status == "Classified"
    )

    human_review_count = sum(
        1 for email in emails if email.requires_human_review
    )

    attachment_email_count = sum(
        1 for email in emails if email.has_attachment
    )

    sla_status_distribution = Counter()

    for email_record in emails:
        email = email_to_dict(email_record)
        classification = classify_email(email)
        sla = calculate_sla(email, classification)
        sla_status_distribution[sla["status_label"]] += 1

    sla_due_soon_count = sla_status_distribution.get("Yaklaşıyor", 0)
    sla_overdue_count = sla_status_distribution.get("Gecikti", 0)

    imported_email_count = system_log_action_distribution.get(
        "EMAIL_IMPORTED",
        0,
    )

    processed_email_count = system_log_action_distribution.get(
        "EMAIL_PROCESSED",
        0,
    )

    latest_logs = (
        db.query(SystemLog)
        .order_by(SystemLog.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_emails": total_emails,
        "imported_email_count": imported_email_count,
        "processed_email_count": processed_email_count,
        "pending_review_count": pending_review_count,
        "approved_count": approved_count,
        "corrected_count": corrected_count,
        "classified_count": classified_count,
        "human_review_count": human_review_count,
        "attachment_email_count": attachment_email_count,
        "sla_due_soon_count": sla_due_soon_count,
        "sla_overdue_count": sla_overdue_count,
        "routing_status_distribution": dict(routing_status_distribution),
        "sla_status_distribution": dict(sla_status_distribution),
        "system_log_action_distribution": dict(system_log_action_distribution),
        "latest_logs": [system_log_to_dict(log) for log in latest_logs],
    }
