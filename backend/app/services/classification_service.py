import unicodedata

from app.services.preprocessing_service import build_classification_text


def normalize_text(text: str) -> str:
   

    text = text.lower()

    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    }

    for turkish_char, english_char in replacements.items():
        text = text.replace(turkish_char, english_char)

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    return text


CLASSIFICATION_RULES = [
    {
        "category": "KVKK Başvurusu",
        "department": "Hukuk Müşavirliği",
        "priority": "Yüksek",
        "requires_human_review": True,
        "keywords": [
            "kvkk",
            "kisisel veri",
            "verilerimin silinmesi",
            "acik riza",
            "veri sorumlusu",
            "kisisel verilerimin",
            "veri ihlali",
        ],
        "explanation": "Mailde KVKK veya kişisel veri ifadeleri geçtiği için Hukuk Müşavirliği önerildi.",
    },
    {
        "category": "Teknik Destek",
        "department": "Bilgi İşlem",
        "priority": "Normal",
        "requires_human_review": False,
        "keywords": [
            "portal",
            "sifre",
            "giris",
            "sistem hatasi",
            "erişim",
            "erisim",
            "erisim sorunu",
            "giris hatasi",
            "web sitesi",
            "baglanti",
            "baglanti sorunu",
            "calismiyor",
            "acilmiyor",
            "hata aliyorum",
            "hata veriyor",
            "erisemiyorum",
            "giremiyorum",
            "yukleyemiyorum",
        ],
        "explanation": "Mailde sistem, portal, giriş veya erişim problemi ifadeleri geçtiği için Bilgi İşlem önerildi.",
    },
    {
        "category": "Basın Talebi",
        "department": "Basın ve Halkla İlişkiler",
        "priority": "Normal",
        "requires_human_review": False,
        "keywords": [
            "basin",
            "roportaj",
            "gazeteci",
            "basin aciklamasi",
            "kurum baskani",
        ],
        "explanation": "Mailde basın, röportaj veya açıklama talebi ifadeleri geçtiği için Basın ve Halkla İlişkiler önerildi.",
    },
    {
        "category": "Satın Alma",
        "department": "Satın Alma",
        "priority": "Normal",
        "requires_human_review": False,
        "keywords": [
            "satin alma",
            "teklif",
            "tedarikci",
            "lisans",
            "ihale",
        ],
        "explanation": "Mailde satın alma, teklif veya tedarik ifadeleri geçtiği için Satın Alma birimi önerildi.",
    },
    {
        "category": "Hukuki Tebligat",
        "department": "Evrak Kayıt",
        "priority": "Kritik",
        "requires_human_review": True,
        "keywords": [
            "mahkeme",
            "tebligat",
            "dava",
            "hukuki",
            "avukat",
            "gereginin yapilmasi",
        ],
        "explanation": "Mailde mahkeme, tebligat veya dava ifadeleri geçtiği için Evrak Kayıt önerildi ve insan onayı gerekli görüldü.",
    },
    {
        "category": "İhbar",
        "department": "İlgili Uzman Daire",
        "priority": "Kritik",
        "requires_human_review": True,
        "keywords": [
            "ihbar",
            "kimligimin gizli",
            "anlasarak fiyat",
            "rakipleriyle",
            "gizli tutulmasini",
        ],
        "explanation": "Mailde ihbar veya gizlilik talebi içeren ifadeler geçtiği için İlgili Uzman Daire önerildi.",
    },
    {
        "category": "Fatura / Ödeme",
        "department": "Strateji / Mali İşler",
        "priority": "Normal",
        "requires_human_review": False,
        "keywords": [
            "fatura",
            "odeme",
            "muhasebe",
            "fatura numarasi",
            "tutar",
        ],
        "explanation": "Mailde fatura veya ödeme ifadeleri geçtiği için Strateji / Mali İşler önerildi.",
    },
    {
        "category": "İnsan Kaynakları",
        "department": "İnsan Kaynakları",
        "priority": "Düşük",
        "requires_human_review": False,
        "keywords": [
            "staj",
            "cv",
            "personel alimi",
            "uzman yardimcisi",
            "ise alim",
        ],
        "explanation": "Mailde staj, CV veya personel alımı ifadeleri geçtiği için İnsan Kaynakları önerildi.",
    },
    {
    "category": "Genel Başvuru",
    "department": "İlgili Uzman Daire",
    "priority": "Normal",
    "requires_human_review": False,
    "keywords": [
        "toplanti",
        "toplanti daveti",
        "is birligi",
        "gorusmek",
        "kurum temsilcileri",
        "rekabet hukuku alaninda",
    ],
    "explanation": "Mailde toplantı, iş birliği veya görüşme talebi ifadeleri geçtiği için İlgili Uzman Daire önerildi.",
},
    {
        "category": "Bilgi Edinme",
        "department": "İlgili Uzman Daire",
        "priority": "Normal",
        "requires_human_review": False,
        "keywords": [
            "bilgi edinme",
            "karar",
            "kurul karari",
            "aciklama talep",
            "karar metni",
            "karar hakkinda",
        ],
        "explanation": "Mailde bilgi edinme veya karar hakkında açıklama talebi olduğu için İlgili Uzman Daire önerildi.",
    },
    {
    "category": "Şikayet",
    "department": "İlgili Uzman Daire",
    "priority": "Yüksek",
    "requires_human_review": True,
    "keywords": [
        "sikayet",
        "haksiz fiyat",
        "haksiz fiyat uygulamasi",
        "piyasada",
        "konunun incelenmesini",
        "firma tarafindan",
        "rekabet ihlali",
    ],
    "explanation": "Mailde şikayet, haksız fiyat veya rekabet ihlali ifadeleri geçtiği için İlgili Uzman Daire önerildi.",
},
{
    "category": "Evrak Kayıt",
    "department": "Evrak Kayıt",
    "priority": "Normal",
    "requires_human_review": False,
    "keywords": [
        "eksik belge",
        "belgeler ekte",
        "ekte sunulmustur",
        "basvuru numarasi",
        "dosya numarasi",
        "kayit numarasi",
    ],
    "explanation": "Mailde evrak, belge veya başvuru numarası ifadeleri geçtiği için Evrak Kayıt önerildi.",
},
]


TECHNICAL_INTENT_KEYWORDS = [
    "acilmiyor",
    "calismiyor",
    "hata aliyorum",
    "hata veriyor",
    "hata mesaji",
    "erisim sorunu",
    "erisemiyorum",
    "giremiyorum",
    "yukleyemiyorum",
    "gonderemiyorum",
    "baglanti sorunu",
    "portal hatasi",
    "giris hatasi",
    "ekran bos",
    "sistem uyarisi",
]

TECHNICAL_CONTEXT_TOPICS = [
    "kvkk",
    "kisisel veri",
    "fatura",
    "odeme",
    "ihale",
    "satin alma",
    "tebligat",
    "mahkeme",
    "basvuru formu",
    "form",
]

FINANCIAL_INTENT_KEYWORDS = [
    "odeme durumu",
    "odeme bilgisi",
    "odeme yapilmasi",
    "fatura numarasi",
    "tutar",
    "dekont",
    "muhasebe",
    "vade",
]


def find_matching_signals(normalized_text: str, keywords: list[str]) -> list[str]:
    return [
        keyword
        for keyword in keywords
        if normalize_text(keyword) in normalized_text
    ]


def merge_keywords(existing_keywords: list[str], new_keywords: list[str]) -> list[str]:
    merged_keywords = []

    for keyword in existing_keywords + new_keywords:
        if keyword not in merged_keywords:
            merged_keywords.append(keyword)

    return merged_keywords


def calculate_confidence(match_count: int) -> float:
    """
    Eşleşen anahtar kelime sayısına göre basit bir güven skoru üretir.
    Bu şu an gerçek AI skoru değil, kural tabanlı basit bir skordur.
    """

    if match_count == 0:
        return 0.40

    score = 0.55 + (match_count * 0.12)

    if score > 0.95:
        score = 0.95

    return round(score, 2)


def apply_intent_routing_overrides(result: dict, normalized_text: str) -> dict:
    """
    Aynı mailde birden fazla konu kelimesi geçebilir. Bu katman konu adından çok
    talebin eylemine bakarak daha doğru birime yönlendirme yapar.
    """

    technical_intent_matches = find_matching_signals(
        normalized_text,
        TECHNICAL_INTENT_KEYWORDS,
    )
    technical_topic_matches = find_matching_signals(
        normalized_text,
        TECHNICAL_CONTEXT_TOPICS,
    )
    financial_intent_matches = find_matching_signals(
        normalized_text,
        FINANCIAL_INTENT_KEYWORDS,
    )

    if technical_intent_matches and (
        result["category"] != "Teknik Destek" or technical_topic_matches
    ):
        result.update(
            {
                "category": "Teknik Destek",
                "department": "Bilgi İşlem",
                "priority": "Normal",
                "requires_human_review": False,
                "confidence_score": max(result.get("confidence_score", 0), 0.86),
                "contextual_override": True,
                "context_signal": "Teknik hata eylemi",
                "matched_keywords": merge_keywords(
                    result.get("matched_keywords", []),
                    technical_intent_matches,
                ),
                "explanation": (
                    "Mailde başka bir konuya ait ifadeler geçse de ana eylem "
                    "erişim, hata veya sistem kullanımı problemi olduğu için "
                    "Bilgi İşlem önerildi."
                ),
            }
        )

        return result

    if financial_intent_matches and result["category"] != "Fatura / Ödeme":
        result.update(
            {
                "category": "Fatura / Ödeme",
                "department": "Strateji / Mali İşler",
                "priority": "Normal",
                "requires_human_review": False,
                "confidence_score": max(result.get("confidence_score", 0), 0.84),
                "contextual_override": True,
                "context_signal": "Mali işlem eylemi",
                "matched_keywords": merge_keywords(
                    result.get("matched_keywords", []),
                    financial_intent_matches,
                ),
                "explanation": (
                    "Maildeki ana istek ödeme, fatura numarası, tutar veya "
                    "muhasebe bilgisinin incelenmesi olduğu için Strateji / "
                    "Mali İşler önerildi."
                ),
            }
        )

    return result


def apply_contextual_overrides(result: dict, normalized_text: str, email: dict) -> dict:
    """
    Kategori doğru bulunduktan sonra özel durumlara göre
    öncelik veya insan onayı bilgisini günceller.
    """

    result = apply_intent_routing_overrides(result, normalized_text)

    # Kişisel veri ihlali kritik kabul edilir.
    if "veri ihlali" in normalized_text or "ucuncu kisilerle paylasildigini" in normalized_text:
        result["priority"] = "Kritik"
        result["requires_human_review"] = True
        result["explanation"] += " Ayrıca kişisel veri ihlali ifadesi bulunduğu için öncelik Kritik olarak güncellendi."

    # Ekli ve karar/açıklama içeren bilgi edinme talepleri insan onayına düşsün.
    if result["category"] == "Bilgi Edinme" and email.get("has_attachment"):
        result["requires_human_review"] = True
        result["explanation"] += " Mail ek içerdiği için insan onayı gerekli görüldü."

    # Web sitesi bağlantı/hata bildirimi düşük öncelikli teknik destek olsun.
    # Ama portal giriş / şifre sorunları düşük değil, normal öncelikli kalmalı.
    if result["category"] == "Teknik Destek":
        is_website_issue = (
            "web sitesi" in normalized_text
            or "iletisim sayfasi" in normalized_text
        )

        is_login_or_password_issue = (
            "portal" in normalized_text
            or "sifre" in normalized_text
            or "giris" in normalized_text
        )

        if is_website_issue and not is_login_or_password_issue:
            result["priority"] = "Düşük"
            result["explanation"] += " Web sitesi bağlantı bildirimi olduğu için öncelik Düşük olarak güncellendi."

    # Basın açıklaması talebi daha öncelikli değerlendirilsin.
    if result["category"] == "Basın Talebi":
        high_priority_press_keywords = [
            "basin aciklamasi",
            "son yayimlanan karar",
            "resmi bir basin aciklamasi",
        ]

        if any(keyword in normalized_text for keyword in high_priority_press_keywords):
            result["priority"] = "Yüksek"
            result["explanation"] += " Basın açıklaması talebi olduğu için öncelik Yüksek olarak güncellendi."

    return result


def classify_email(email: dict) -> dict:
    """
    Bir maili alır, subject + body alanlarını birlikte inceler,
    en uygun kategori ve birimi döndürür.
    """

    combined_text = build_classification_text(email)
    normalized_text = normalize_text(combined_text) 

    best_result = None
    best_match_count = 0

    for rule in CLASSIFICATION_RULES:
        matched_keywords = []

        for keyword in rule["keywords"]:
            normalized_keyword = normalize_text(keyword)

            if normalized_keyword in normalized_text:
                matched_keywords.append(keyword)

        match_count = len(matched_keywords)

        if match_count > best_match_count:
            best_match_count = match_count
            best_result = {
                "category": rule["category"],
                "department": rule["department"],
                "priority": rule["priority"],
                "requires_human_review": rule["requires_human_review"],
                "matched_keywords": matched_keywords,
                "confidence_score": calculate_confidence(match_count),
                "explanation": rule["explanation"],
            }

    if best_result is None:
        return {
            "category": "Genel Başvuru",
            "department": "Evrak Kayıt",
            "priority": "Düşük",
            "requires_human_review": False,
            "matched_keywords": [],
            "confidence_score": 0.40,
            "explanation": "Mail belirli bir kategoriyle güçlü şekilde eşleşmediği için manuel inceleme önerildi.",
        }
    best_result = apply_contextual_overrides(best_result, normalized_text, email)
    return best_result
