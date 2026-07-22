import json
import os
import ssl
import urllib.error
import urllib.request

from app.services.classification_service import normalize_text
from app.services.information_extraction_service import extract_structured_information
from app.services.preprocessing_service import build_classification_text
from app.services.summary_service import generate_summary


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-5.6-luna"
ALLOWED_CATEGORIES = [
    "KVKK Başvurusu",
    "Teknik Destek",
    "Basın Talebi",
    "Satın Alma",
    "Hukuki Tebligat",
    "İhbar",
    "Fatura / Ödeme",
    "İnsan Kaynakları",
    "Genel Başvuru",
    "Bilgi Edinme",
    "Şikayet",
    "Evrak Kayıt",
]
ALLOWED_DEPARTMENTS = [
    "Hukuk Müşavirliği",
    "Bilgi İşlem",
    "Basın ve Halkla İlişkiler",
    "Satın Alma",
    "Evrak Kayıt",
    "İlgili Uzman Daire",
    "Strateji / Mali İşler",
    "İnsan Kaynakları",
]
CRITICAL_CATEGORIES = [
    "KVKK Başvurusu",
    "Hukuki Tebligat",
    "İhbar",
]


AMBIGUOUS_CATEGORIES = [
    "Genel Başvuru",
    "Bilgi Edinme",
    "Evrak Kayıt",
]


class LlmServiceError(RuntimeError):
    pass


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def clamp_confidence_score(value) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.70

    if score < 0:
        return 0

    if score > 1:
        return 1

    return round(score, 2)


def safe_text(value, fallback: str = "") -> str:
    if value is None:
        return fallback

    text = str(value).strip()
    return text or fallback


def get_openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY")


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)


def build_ssl_context():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ModuleNotFoundError:
        try:
            from pip._vendor import certifi as pip_certifi

            return ssl.create_default_context(cafile=pip_certifi.where())
        except Exception:
            return ssl.create_default_context()


def should_use_ai(rule_classification: dict) -> bool:
    """
    Kural tabanlı sonuç yeterince güvenli değilse veya kategori belirsizse
    AI destekli analiz önerilir.
    """

    confidence_score = rule_classification["confidence_score"]
    category = rule_classification["category"]

    if confidence_score < 0.85:
        return True

    if category in AMBIGUOUS_CATEGORIES and confidence_score < 0.95:
        return True

    return False


def get_ai_usage_reason(rule_classification: dict) -> str:
    confidence_score = rule_classification["confidence_score"]
    category = rule_classification["category"]

    if confidence_score < 0.60:
        return (
            "Kural tabanlı güven skoru düşük olduğu için AI destekli sınıflandırma "
            "ve manuel kontrol önerildi."
        )

    if confidence_score < 0.85:
        return (
            "Kural tabanlı güven skoru orta seviyede olduğu için AI destekli analiz "
            "önerildi."
        )

    if category in AMBIGUOUS_CATEGORIES:
        return (
            "Mail konusu birden fazla birimle ilişkili olabileceği için AI destekli "
            "bağlam analizi önerildi."
        )

    return "Kural tabanlı sonuç yeterince güvenilir olduğu için AI kullanımı gerekli görülmedi."


def create_mock_ai_summary(email: dict, rule_classification: dict) -> str:
    return generate_summary(email, rule_classification)


def create_mock_ai_explanation(email: dict, ai_category: str, ai_department: str) -> str:
    subject = email.get("subject", "")

    return (
        f"AI mock katmanı, mail konusu ve içerik bağlamını değerlendirerek "
        f"'{subject}' başlıklı mail için '{ai_category}' kategorisini ve "
        f"'{ai_department}' birimini önermiştir."
    )


def mock_ai_classify_email(email: dict, rule_classification: dict) -> dict:
    """
    Gerçek AI servisi yerine çalışan mock AI katmanıdır.

    Amaç:
    - İleride LLM/API bağlanacak yeri hazır tutmak
    - Belirsiz maillerde ikinci görüş üretmek
    - Demo ve raporda AI mimarisini göstermek
    """

    normalized_text = normalize_text(build_classification_text(email))

    ai_category = rule_classification["category"]
    ai_department = rule_classification["department"]
    ai_priority = rule_classification["priority"]
    ai_confidence_score = min(rule_classification["confidence_score"] + 0.03, 0.98)

    if contains_any(
        normalized_text,
        [
            "kurul karari",
            "karar hakkinda",
            "aciklama talebi",
            "bilgi edinme",
            "kararin paylasilmasi",
        ],
    ):
        ai_category = "Bilgi Edinme"
        ai_department = "İlgili Uzman Daire"
        ai_priority = "Normal"
        ai_confidence_score = 0.88

    elif contains_any(
        normalized_text,
        [
            "toplanti",
            "randevu",
            "gorusme",
            "ziyaret",
        ],
    ):
        ai_category = "Toplantı Daveti"
        ai_department = "İlgili Uzman Daire"
        ai_priority = "Normal"
        ai_confidence_score = 0.84

    elif contains_any(
        normalized_text,
        [
            "proje",
            "is birligi",
            "iş birliği",
            "ortak calisma",
            "kurumsal isbirligi",
        ],
    ):
        ai_category = "Kurumsal İş Birliği"
        ai_department = "Strateji Geliştirme"
        ai_priority = "Normal"
        ai_confidence_score = 0.82

    elif contains_any(
        normalized_text,
        [
            "hukuki gorus",
            "mevzuat hakkinda gorus",
            "hukuki degerlendirme",
        ],
    ):
        ai_category = "Hukuki Görüş"
        ai_department = "Hukuk Müşavirliği"
        ai_priority = "Yüksek"
        ai_confidence_score = 0.86

    elif contains_any(
        normalized_text,
        [
            "out of office",
            "otomatik cevap",
            "abonelikten cik",
            "kampanya",
            "reklam",
        ],
    ):
        ai_category = "Genel Başvuru"
        ai_department = "Evrak Kayıt"
        ai_priority = "Düşük"
        ai_confidence_score = 0.78

    requires_human_review = rule_classification.get("requires_human_review", False)

    if ai_category in CRITICAL_CATEGORIES:
        requires_human_review = True

    return {
        "ai_category": ai_category,
        "ai_department": ai_department,
        "ai_priority": ai_priority,
        "ai_confidence_score": round(ai_confidence_score, 2),
        "ai_requires_human_review": requires_human_review,
        "ai_summary": create_mock_ai_summary(email, rule_classification),
        "ai_explanation": create_mock_ai_explanation(
            email=email,
            ai_category=ai_category,
            ai_department=ai_department,
        ),
        "source": "demo",
        "evidence": rule_classification.get("matched_keywords", []),
    }


def build_llm_input_package(email: dict, rule_classification: dict) -> dict:
    extracted_information = extract_structured_information(email, rule_classification)

    return {
        "subject": email.get("subject"),
        "sender": email.get("sender"),
        "source_mailbox": email.get("source_mailbox"),
        "body": email.get("body"),
        "attachments": {
            "has_attachment": email.get("has_attachment", False),
            "attachment_names": email.get("attachment_names", []),
            "attachment_texts": email.get("attachment_texts", []),
        },
        "rule_based_classification": rule_classification,
        "extracted_information": extracted_information,
        "allowed_categories": ALLOWED_CATEGORIES,
        "allowed_departments": ALLOWED_DEPARTMENTS,
    }


def build_llm_prompt(input_package: dict) -> str:
    return (
        "Rekabet Kurumu için kurumsal e-posta sınıflandırma ve özetleme yap. "
        "Sadece izinli kategori ve birimlerden seçim yap. Kritik veya hassas içerikte "
        "insan onayı öner. E-posta gövdesi kısa ve bilgi eklerdeyse bunu özette belirt. "
        "Yanıtını yalnızca istenen JSON şemasına uygun üret.\n\n"
        f"Girdi:\n{json.dumps(input_package, ensure_ascii=False)}"
    )


def get_llm_response_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "category": {"type": "string", "enum": ALLOWED_CATEGORIES},
            "department": {"type": "string", "enum": ALLOWED_DEPARTMENTS},
            "priority": {"type": "string", "enum": ["Düşük", "Normal", "Yüksek", "Kritik"]},
            "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
            "requires_human_review": {"type": "boolean"},
            "summary": {"type": "string"},
            "explanation": {"type": "string"},
            "evidence": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "category",
            "department",
            "priority",
            "confidence_score",
            "requires_human_review",
            "summary",
            "explanation",
            "evidence",
        ],
    }


def extract_response_text(response_data: dict) -> str:
    if response_data.get("output_text"):
        return response_data["output_text"]

    text_parts = []

    for output_item in response_data.get("output", []):
        for content_item in output_item.get("content", []):
            if content_item.get("type") in {"output_text", "text"}:
                text_parts.append(content_item.get("text", ""))

    return "".join(text_parts).strip()


def call_openai_llm(input_package: dict) -> dict:
    api_key = get_openai_api_key()

    if not api_key:
        raise LlmServiceError("OPENAI_API_KEY is not configured.")

    payload = {
        "model": get_openai_model(),
        "input": [
            {
                "role": "system",
                "content": (
                    "Kurumsal e-posta operasyonları için güvenli ve denetlenebilir "
                    "sınıflandırma yapan bir asistansın. Kişisel verileri gereksiz "
                    "tekrar etme, sadece operasyonel özet ve yönlendirme gerekçesi üret."
                ),
            },
            {
                "role": "user",
                "content": build_llm_prompt(input_package),
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "smartmail_llm_analysis",
                "schema": get_llm_response_schema(),
                "strict": True,
            }
        },
    }

    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=20,
            context=build_ssl_context(),
        ) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise LlmServiceError(f"OpenAI API returned {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise LlmServiceError(f"OpenAI API request failed: {error}") from error

    response_text = extract_response_text(response_data)

    if not response_text:
        raise LlmServiceError("OpenAI API returned an empty response.")

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as error:
        raise LlmServiceError("OpenAI API response was not valid JSON.") from error


def normalize_llm_result(
    llm_result: dict,
    email: dict,
    rule_classification: dict,
    source: str,
) -> dict:
    category = llm_result.get("category")
    department = llm_result.get("department")
    priority = llm_result.get("priority")

    if category not in ALLOWED_CATEGORIES:
        category = rule_classification["category"]

    if department not in ALLOWED_DEPARTMENTS:
        department = rule_classification["department"]

    if priority not in ["Düşük", "Normal", "Yüksek", "Kritik"]:
        priority = rule_classification["priority"]

    requires_human_review = bool(llm_result.get("requires_human_review"))

    if category in CRITICAL_CATEGORIES:
        requires_human_review = True

    return {
        "ai_category": category,
        "ai_department": department,
        "ai_priority": priority,
        "ai_confidence_score": clamp_confidence_score(
            llm_result.get("confidence_score")
        ),
        "ai_requires_human_review": requires_human_review,
        "ai_summary": safe_text(
            llm_result.get("summary"),
            create_mock_ai_summary(email, rule_classification),
        ),
        "ai_explanation": safe_text(
            llm_result.get("explanation"),
            create_mock_ai_explanation(
                email=email,
                ai_category=category,
                ai_department=department,
            ),
        ),
        "source": source,
        "evidence": llm_result.get("evidence", []),
    }


def classify_email_with_llm_or_demo(email: dict, rule_classification: dict) -> tuple[dict, dict]:
    input_package = build_llm_input_package(email, rule_classification)

    try:
        llm_result = call_openai_llm(input_package)
        return normalize_llm_result(
            llm_result=llm_result,
            email=email,
            rule_classification=rule_classification,
            source="openai_api",
        ), {
            "provider": "OpenAI",
            "model": get_openai_model(),
            "status": "connected",
        }
    except LlmServiceError as error:
        demo_result = mock_ai_classify_email(
            email=email,
            rule_classification=rule_classification,
        )
        return demo_result, {
            "provider": "OpenAI",
            "model": get_openai_model(),
            "status": "demo_fallback",
            "reason": str(error),
        }


def compare_rule_and_ai_results(
    rule_classification: dict,
    ai_classification: dict,
) -> dict:
    category_match = rule_classification["category"] == ai_classification["ai_category"]
    department_match = rule_classification["department"] == ai_classification["ai_department"]
    priority_match = rule_classification["priority"] == ai_classification["ai_priority"]

    if category_match and department_match and priority_match:
        agreement_level = "Tam uyum"
    elif category_match and department_match:
        agreement_level = "Yüksek uyum"
    elif category_match:
        agreement_level = "Kısmi uyum"
    else:
        agreement_level = "Farklı öneri"

    return {
        "category_match": category_match,
        "department_match": department_match,
        "priority_match": priority_match,
        "agreement_level": agreement_level,
    }


def create_final_ai_recommendation(
    rule_classification: dict,
    ai_classification: dict,
    comparison: dict,
) -> dict:
    """
    AI sonucu doğrudan nihai karar yapmıyoruz.
    Kural tabanlı sistem ana karar olarak kalıyor.
    AI sadece destekleyici öneri üretiyor.
    """

    if rule_classification["category"] in CRITICAL_CATEGORIES:
        final_decision_source = "Rule-based priority"
        final_note = (
            "Mail kritik kategoriye girdiği için kural tabanlı karar öncelikli tutuldu "
            "ve insan onayı zorunlu bırakıldı."
        )

    elif comparison["agreement_level"] in ["Tam uyum", "Yüksek uyum"]:
        final_decision_source = "Rule + AI agreement"
        final_note = (
            "Kural tabanlı sistem ve yapay zeka katmanı benzer sonuç verdiği için "
            "karar güvenilir kabul edildi."
        )

    elif rule_classification["confidence_score"] >= 0.85:
        final_decision_source = "Rule-based result"
        final_note = (
            "Kural tabanlı güven skoru yüksek olduğu için ana karar kural tabanlı "
            "sonuçtan alındı."
        )

    else:
        final_decision_source = "Human review required"
        final_note = (
            "Kural ve AI önerileri arasında fark bulunduğu veya güven skoru düşük olduğu "
            "için operatör incelemesi önerildi."
        )

    return {
        "final_decision_source": final_decision_source,
        "final_note": final_note,
        "human_review_required": (
            rule_classification.get("requires_human_review", False)
            or ai_classification.get("ai_requires_human_review", False)
            or final_decision_source == "Human review required"
        ),
    }


def analyze_email_with_mock_ai(email: dict, rule_classification: dict) -> dict:
    ai_recommended = should_use_ai(rule_classification)
    ai_usage_reason = get_ai_usage_reason(rule_classification)

    ai_classification, llm_connection = classify_email_with_llm_or_demo(
        email=email,
        rule_classification=rule_classification,
    )

    comparison = compare_rule_and_ai_results(
        rule_classification=rule_classification,
        ai_classification=ai_classification,
    )

    final_recommendation = create_final_ai_recommendation(
        rule_classification=rule_classification,
        ai_classification=ai_classification,
        comparison=comparison,
    )

    return {
        "ai_mode": ai_classification.get("source", "demo"),
        "llm_connection": llm_connection,
        "ai_recommended": ai_recommended,
        "ai_usage_reason": ai_usage_reason,
        "rule_based_classification": rule_classification,
        "llm_classification": ai_classification,
        "mock_ai_classification": ai_classification,
        "rule_ai_comparison": comparison,
        "final_recommendation": final_recommendation,
    }
