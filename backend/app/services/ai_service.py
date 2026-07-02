from app.services.classification_service import normalize_text
from app.services.preprocessing_service import build_classification_text


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


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


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
    category = rule_classification["category"]
    department = rule_classification["department"]

    return (
        f"AI destekli analiz, mailin '{category}' kapsamında değerlendirilebileceğini "
        f"ve öncelikli olarak '{department}' birimine yönlendirilebileceğini öngörmektedir."
    )


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
            "Kural tabanlı sistem ve AI mock katmanı benzer sonuç verdiği için "
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

    ai_classification = mock_ai_classify_email(
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
        "ai_mode": "mock",
        "ai_recommended": ai_recommended,
        "ai_usage_reason": ai_usage_reason,
        "rule_based_classification": rule_classification,
        "mock_ai_classification": ai_classification,
        "rule_ai_comparison": comparison,
        "final_recommendation": final_recommendation,
    }