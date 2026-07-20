import re

from app.services.attachment_analysis_service import analyze_attachments
from app.services.classification_service import normalize_text
from app.services.information_extraction_service import extract_information_from_text
from app.services.preprocessing_service import build_classification_text, clean_email_body
from app.services.sla_service import calculate_sla


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def shorten_text(text: str, max_length: int = 180) -> str:
    if len(text) <= max_length:
        return text

    return text[:max_length].strip() + "..."


def normalize_whitespace(text: str) -> str:
    return " ".join((text or "").split())


def lower_first_letter(text: str) -> str:
    if not text:
        return text

    return text[0].lower() + text[1:]


def remove_entity_label(text: str) -> str:
    return re.sub(
        r"^(?:başvuru|basvuru|karar)\s*(?:no|numarası|numarasi)?\s*[:\s-]+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def join_limited_values(values: list[str], limit: int = 3) -> str:
    cleaned_values = []

    for value in values or []:
        normalized_value = remove_entity_label(normalize_whitespace(str(value)))

        if normalized_value and normalized_value not in cleaned_values:
            cleaned_values.append(normalized_value)

    if not cleaned_values:
        return ""

    visible_values = cleaned_values[:limit]
    result = ", ".join(visible_values)
    hidden_count = len(cleaned_values) - len(visible_values)

    if hidden_count > 0:
        result += f" ve {hidden_count} kayıt daha"

    return result


def get_sender_label(email: dict, extracted: dict) -> str:
    return (
        extracted.get("sender_institution")
        or extracted.get("sender")
        or extracted.get("sender_email")
        or email.get("sender")
        or "Gönderen"
    )


def detect_message_signal(email: dict) -> str:
    body = normalize_whitespace(clean_email_body(email.get("body", "")))
    normalized_body = normalize_text(body)

    if email.get("has_attachment") and len(body) < 90:
        return "Mail gövdesi sınırlı bilgi içeriyor; ek analizi karar için belirleyici olabilir."

    if contains_any(normalized_body, ["ekte sunulmustur", "ekte yer almaktadir", "ekinde sunuyorum"]):
        return "Gönderici asıl içeriğin eklerde yer aldığını belirtiyor."

    if contains_any(normalized_body, ["acil", "ivedi", "sure dolmak", "son gun"]):
        return "Metinde süre hassasiyeti veya ivedilik sinyali bulunuyor."

    return ""


def build_entity_sentence(extracted: dict) -> str:
    entity_parts = []

    if extracted.get("application_numbers"):
        entity_parts.append(
            f"başvuru numarası: {join_limited_values(extracted['application_numbers'])}"
        )

    if extracted.get("file_numbers"):
        entity_parts.append(f"dosya numarası: {join_limited_values(extracted['file_numbers'])}")

    if extracted.get("decision_numbers"):
        entity_parts.append(
            f"karar numarası: {join_limited_values(extracted['decision_numbers'])}"
        )

    if extracted.get("dates"):
        entity_parts.append(f"tarih: {join_limited_values(extracted['dates'])}")

    if extracted.get("related_legislation"):
        entity_parts.append(
            f"mevzuat: {join_limited_values(extracted['related_legislation'])}"
        )

    if extracted.get("complained_party"):
        entity_parts.append(f"şikayet edilen taraf: {extracted['complained_party']}")

    if extracted.get("money_amounts"):
        entity_parts.append(f"tutar: {join_limited_values(extracted['money_amounts'])}")

    if not entity_parts:
        return ""

    return f"Öne çıkan bilgiler: {'; '.join(entity_parts)}."


def build_attachment_sentence(email: dict, extracted: dict) -> str:
    attachment_names = extracted.get("attachment_names") or email.get("attachment_names") or []

    if not email.get("has_attachment") and not attachment_names:
        return "Ek bulunmuyor."

    if attachment_names:
        return f"Ekler: {join_limited_values(attachment_names)}."

    return "Ek olduğu bildiriliyor ancak dosya adı sistemde yer almıyor."


def generate_summary(email: dict, classification: dict) -> str:
    category = classification["category"]
    department = classification["department"]
    priority = classification["priority"]

    cleaned_body = clean_email_body(email.get("body", ""))
    normalized_text = normalize_text(build_classification_text(email))
    extracted = extract_information_from_text(email, classification)
    sender_label = get_sender_label(email, extracted)
    subject = normalize_whitespace(email.get("subject", ""))
    requested_action = extracted.get("requested_action") or f"{category} değerlendirmesi"
    entity_sentence = build_entity_sentence(extracted)
    attachment_sentence = build_attachment_sentence(email, extracted)
    message_signal = detect_message_signal(email)

    summary_parts = [
        (
            f"{sender_label}, "
            f"{subject or category} konulu e-postada "
            f"{lower_first_letter(requested_action)} iletiyor."
        ),
    ]

    if entity_sentence:
        summary_parts.append(entity_sentence)

    summary_parts.append(attachment_sentence)

    if message_signal:
        summary_parts.append(message_signal)

    summary_parts.append(
        f"Önerilen işlem: {department} tarafından {priority.lower()} öncelikle değerlendirilmesi."
    )

    contextual_summary = " ".join(summary_parts)

    if category == "KVKK Başvurusu":
        return contextual_summary

    if category == "Teknik Destek":
        return contextual_summary

    if category == "Basın Talebi":
        return contextual_summary

    if category == "Satın Alma":
        return contextual_summary

    if category == "Hukuki Tebligat":
        return contextual_summary

    if category == "Şikayet":
        return contextual_summary

    if category == "İhbar":
        return contextual_summary

    if category == "Bilgi Edinme":
        return contextual_summary

    if category in ["Fatura / Ödeme", "Fatura/Ödeme"]:
        return contextual_summary

    if category == "İnsan Kaynakları":
        return contextual_summary

    if category == "Evrak Kayıt":
        return contextual_summary

    if contains_any(normalized_text, ["toplanti", "randevu", "gorusme"]):
        return contextual_summary

    return (
        f"{contextual_summary} "
        f"İçerik özeti: {shorten_text(cleaned_body)}"
    )


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
