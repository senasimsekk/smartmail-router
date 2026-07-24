from datetime import datetime

from app.services.classification_service import classify_email
from app.services.email_analysis_service import analyze_email
from app.services.email_db_service import email_to_dict
from app.services.sla_service import calculate_sla


def get_notification_tone(sla_status: str, priority: str, risk_level: str) -> str:
    if sla_status == "Overdue" or priority == "Kritik" or risk_level == "Kritik":
        return "danger"

    if sla_status == "Due soon" or priority == "Yüksek" or risk_level == "Yüksek":
        return "warning"

    return "neutral"


def get_notification_reason(sla: dict, classification: dict, analysis: dict) -> str:
    if sla["status"] == "Overdue":
        return "SLA süresi aşıldı; kayıt öncelikli işlem kuyruğuna alınmalı."

    if sla["status"] == "Due soon":
        return "SLA son tarihi yaklaşıyor; gecikme oluşmadan takip edilmeli."

    if classification.get("priority") == "Kritik":
        return "Kritik öncelikli kayıt için birim/operatör bildirimi önerilir."

    if analysis.get("risk_level") in ["Kritik", "Yüksek"]:
        return "Risk seviyesi yüksek olduğu için takip bildirimi önerilir."

    return "Operasyonel takip bildirimi önerilir."


def build_sla_notifications(email_records, now: datetime | None = None) -> dict:
    notifications = []

    for email_record in email_records:
        email = email_to_dict(email_record)
        classification = classify_email(email)
        analysis = analyze_email(email, classification)
        sla = calculate_sla(email, classification, now=now)

        if (
            sla["status"] not in ["Overdue", "Due soon"]
            and classification.get("priority") != "Kritik"
            and analysis.get("risk_level") not in ["Kritik", "Yüksek"]
        ):
            continue

        notifications.append(
            {
                "id": f"sla-{email['id']}",
                "email_id": email["id"],
                "subject": email["subject"],
                "sender": email["sender"],
                "department": classification["department"],
                "category": classification["category"],
                "priority": classification["priority"],
                "sla_status": sla["status"],
                "sla_status_label": sla["status_label"],
                "remaining_days": sla["remaining_days"],
                "due_at": sla["due_at"],
                "risk_level": analysis["risk_level"],
                "tone": get_notification_tone(
                    sla_status=sla["status"],
                    priority=classification["priority"],
                    risk_level=analysis["risk_level"],
                ),
                "reason": get_notification_reason(sla, classification, analysis),
                "channel": "Sistem içi bildirim",
            }
        )

    tone_rank = {"danger": 0, "warning": 1, "neutral": 2}
    notifications.sort(
        key=lambda item: (
            tone_rank.get(item["tone"], 3),
            item["remaining_days"],
            item["email_id"],
        )
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "mode": "Sistem içi bildirim simülasyonu",
        "summary": {
            "total": len(notifications),
            "overdue": sum(
                item["sla_status"] == "Overdue" for item in notifications
            ),
            "due_soon": sum(
                item["sla_status"] == "Due soon" for item in notifications
            ),
            "critical": sum(item["tone"] == "danger" for item in notifications),
        },
        "notifications": notifications,
    }
