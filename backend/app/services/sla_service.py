from datetime import datetime, timedelta


SLA_POLICIES = {
    "Hukuki Tebligat": {
        "days": 1,
        "policy_name": "Hukuki tebligat hızlı işlem",
    },
    "İhbar": {
        "days": 3,
        "policy_name": "İhbar ön inceleme",
    },
    "Teknik Destek": {
        "days": 2,
        "policy_name": "Teknik destek yanıt süresi",
    },
    "Basın Talebi": {
        "days": 2,
        "policy_name": "Basın talebi yanıt süresi",
    },
    "Evrak Kayıt": {
        "days": 3,
        "policy_name": "Evrak kayıt işlem süresi",
    },
    "Fatura / Ödeme": {
        "days": 5,
        "policy_name": "Mali işlem değerlendirme",
    },
    "Fatura/Ödeme": {
        "days": 5,
        "policy_name": "Mali işlem değerlendirme",
    },
    "Satın Alma": {
        "days": 5,
        "policy_name": "Satın alma değerlendirme",
    },
    "Şikayet": {
        "days": 7,
        "policy_name": "Şikayet inceleme süresi",
    },
    "İnsan Kaynakları": {
        "days": 7,
        "policy_name": "İK başvuru değerlendirme",
    },
    "Genel Başvuru": {
        "days": 7,
        "policy_name": "Genel başvuru yanıt süresi",
    },
    "Bilgi Edinme": {
        "days": 15,
        "policy_name": "Bilgi edinme yanıt süresi",
    },
    "KVKK Başvurusu": {
        "days": 30,
        "policy_name": "KVKK başvuru yasal süre",
    },
}

DEFAULT_SLA_POLICY = {
    "days": 7,
    "policy_name": "Standart başvuru yanıt süresi",
}

CLOSED_ROUTING_STATUSES = {"Approved", "Routed", "Completed", "Archived"}


def parse_created_at(value) -> datetime:
    if isinstance(value, datetime):
        return value

    if isinstance(value, str) and value:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(
            tzinfo=None
        )

    return datetime.utcnow()


def calculate_sla(email: dict, classification: dict, now: datetime | None = None) -> dict:
    category = classification.get("category") or "Genel Başvuru"
    policy = SLA_POLICIES.get(category, DEFAULT_SLA_POLICY)
    created_at = parse_created_at(email.get("created_at"))
    current_time = now or datetime.utcnow()
    due_at = created_at + timedelta(days=policy["days"])
    remaining_days = (due_at.date() - current_time.date()).days

    routing_status = email.get("routing_status")

    if routing_status in CLOSED_ROUTING_STATUSES:
        status = "Closed"
        status_label = "Kapandı"
        severity = "closed"
    elif remaining_days < 0:
        status = "Overdue"
        status_label = "Gecikti"
        severity = "critical"
    elif remaining_days <= 1:
        status = "Due soon"
        status_label = "Yaklaşıyor"
        severity = "warning"
    else:
        status = "On time"
        status_label = "Zamanında"
        severity = "normal"

    return {
        "category": category,
        "policy_name": policy["policy_name"],
        "sla_days": policy["days"],
        "created_at": created_at.isoformat(),
        "due_at": due_at.isoformat(),
        "remaining_days": remaining_days,
        "status": status,
        "status_label": status_label,
        "severity": severity,
    }
