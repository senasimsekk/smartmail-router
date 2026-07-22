from app.services.attachment_analysis_service import analyze_attachments
from app.services.classification_service import normalize_text
from app.services.preprocessing_service import build_classification_text
from app.services.summary_service import generate_summary
from app.services.sla_service import calculate_sla


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def detect_risk(email: dict, classification: dict) -> dict:
    normalized_text = normalize_text(build_classification_text(email))

    risk_level = "Düşük"
    risk_reasons = []

    if classification["priority"] == "Kritik":
        risk_level = "Kritik"
        risk_reasons.append("Mail kritik öncelikli olarak sınıflandırıldı.")

    if classification["category"] in ["Hukuki Tebligat", "İhbar"]:
        risk_level = "Kritik"
        risk_reasons.append("Mail hukuki/ihbar niteliğinde kritik bir konu içeriyor.")

    if classification["category"] == "KVKK Başvurusu":
        if risk_level != "Kritik":
            risk_level = "Yüksek"
        risk_reasons.append("Mail KVKK veya kişisel veri talebi içeriyor.")

    if contains_any(
        normalized_text,
        [
            "veri ihlali",
            "kisisel veri ihlali",
            "tc kimlik",
            "kimlik numarasi",
            "adres",
            "telefon",
            "iban",
            "vergi no",
            "saglik bilgisi",
        ],
    ):
        if risk_level != "Kritik":
            risk_level = "Yüksek"
        risk_reasons.append("Mail hassas veya kişisel veri içerebilir.")

    if contains_any(
        normalized_text,
        [
            "mahkeme",
            "dava",
            "tebligat",
            "icra",
            "kep",
            "uyap",
        ],
    ):
        risk_level = "Kritik"
        risk_reasons.append("Mail hukuki süreç veya resmi tebligat ifadesi içeriyor.")

    if email.get("has_attachment") and classification["category"] in [
        "Hukuki Tebligat",
        "KVKK Başvurusu",
        "İhbar",
        "Bilgi Edinme",
    ]:
        if risk_level == "Düşük":
            risk_level = "Orta"
        risk_reasons.append("Mail eki bulunduğu için içerik ayrıca kontrol edilmeli.")

    if classification.get("requires_human_review"):
        if risk_level == "Düşük":
            risk_level = "Orta"
        risk_reasons.append("Sistem bu mail için insan onayı öneriyor.")

    if not risk_reasons:
        risk_reasons.append("Belirgin bir kritik risk tespit edilmedi.")

    return {
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
    }


def detect_response_requirement(classification: dict) -> dict:
    category = classification["category"]

    response_required_categories = [
        "KVKK Başvurusu",
        "Teknik Destek",
        "Basın Talebi",
        "Satın Alma",
        "Şikayet",
        "İhbar",
        "Bilgi Edinme",
        "Fatura / Ödeme",
        "Fatura/Ödeme",
        "İnsan Kaynakları",
        "Hukuki Tebligat",
    ]

    if category in response_required_categories:
        return {
            "needs_response": True,
            "reason": "Bu kategori genellikle kurum tarafından cevap veya işlem gerektirir.",
        }

    return {
        "needs_response": False,
        "reason": "Bu mail için doğrudan cevap zorunluluğu düşük görünüyor.",
    }


def determine_operation_type(
    email: dict,
    classification: dict,
    response_analysis: dict,
) -> str:
    normalized_text = normalize_text(build_classification_text(email))

    if contains_any(
        normalized_text,
        [
            "spam",
            "reklam",
            "kampanya",
            "abonelikten cik",
            "otomatik cevap",
            "out of office",
        ],
    ):
        return "Reddedilebilir/spam olabilir"

    if classification["category"] in ["Hukuki Tebligat", "Evrak Kayıt"]:
        return "Evrak kaydı gerekiyor"

    if contains_any(
        normalized_text,
        [
            "tebligat",
            "mahkeme",
            "dava",
            "kep",
            "uyap",
            "resmi evrak",
            "ekte sunulmustur",
        ],
    ):
        return "Evrak kaydı gerekiyor"

    if classification.get("requires_human_review"):
        return "Onay gerekiyor"

    if classification["category"] in ["Şikayet", "İhbar"]:
        return "İnceleme gerekiyor"

    if response_analysis["needs_response"]:
        return "Cevap gerekiyor"

    if classification["confidence_score"] >= 0.85:
        return "Yönlendirme gerekiyor"

    if classification["confidence_score"] < 0.60:
        return "Onay gerekiyor"

    return "Bilgi için"


def create_routing_decision(classification: dict, risk_analysis: dict) -> dict:
    primary_department = classification["department"]
    secondary_departments = []

    category = classification["category"]

    if category == "KVKK Başvurusu":
        secondary_departments.append("KVKK Sorumlusu")

    if category == "Hukuki Tebligat":
        secondary_departments.append("Hukuk Müşavirliği")

        if primary_department != "Evrak Kayıt":
            secondary_departments.append("Evrak Kayıt")

    if category in ["Fatura / Ödeme", "Fatura/Ödeme"]:
        secondary_departments.append("Mali İşler")

    if category == "Basın Talebi":
        secondary_departments.append("Basın ve Halkla İlişkiler")

    if risk_analysis["risk_level"] == "Kritik":
        routing_type = "İnsan onayı gerekli"
    elif classification.get("requires_human_review"):
        routing_type = "Operatör onayı gerekli"
    elif classification["confidence_score"] >= 0.85:
        routing_type = "Otomatik yönlendirme uygun"  
    elif 0.60 <= classification["confidence_score"] < 0.85:
        routing_type = "Operatör onayı önerilir"
    else:
        routing_type = "Manuel sınıflandırma gerekli"

    return {
        "primary_department": primary_department,
        "secondary_departments": secondary_departments,
        "routing_type": routing_type,
        "routing_reason": classification.get("explanation"),
    }


def suggest_action(
    classification: dict,
    risk_analysis: dict,
    response_analysis: dict,
) -> str:
    if risk_analysis["risk_level"] == "Kritik":
        return "İnsan onayına düşür ve ilgili birime yönlendirmeden önce operatör kontrolü iste."

    if classification.get("requires_human_review"):
        return "Operatör onayına gönder."

    if classification["confidence_score"] >= 0.85:
        return "Güven skoru yüksek olduğu için önerilen birime otomatik yönlendirilebilir."

    if 0.60 <= classification["confidence_score"] < 0.85:
        return "Güven skoru orta seviyede olduğu için operatör onayı önerilir."

    return "Güven skoru düşük olduğu için manuel sınıflandırma istenmeli."


def analyze_email(email: dict, classification: dict) -> dict:
    summary = generate_summary(email, classification)
    risk_analysis = detect_risk(email, classification)
    response_analysis = detect_response_requirement(classification)
    attachment_analysis = analyze_attachments(email, classification)
    sla = calculate_sla(email, classification)

    operation_type = determine_operation_type(
        email=email,
        classification=classification,
        response_analysis=response_analysis,
    )

    routing_decision = create_routing_decision(
        classification=classification,
        risk_analysis=risk_analysis,
    )

    suggested_action = suggest_action(
        classification=classification,
        risk_analysis=risk_analysis,
        response_analysis=response_analysis,
    )

    return {
        "summary": summary,
        "risk_level": risk_analysis["risk_level"],
        "risk_reasons": risk_analysis["risk_reasons"],
        "needs_response": response_analysis["needs_response"],
        "response_reason": response_analysis["reason"],
        "operation_type": operation_type,
        "routing_decision": routing_decision,
        "suggested_action": suggested_action,
        "attachment_analysis": attachment_analysis,
        "sla": sla,
    }
