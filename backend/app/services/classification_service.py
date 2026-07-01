import unicodedata


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
            "web sitesi",
            "baglanti",
            "calismiyor",
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


def classify_email(email: dict) -> dict:
    """
    Bir maili alır, subject + body alanlarını birlikte inceler,
    en uygun kategori ve birimi döndürür.
    """

    subject = email.get("subject", "")
    body = email.get("body", "")

    combined_text = f"{subject} {body}"
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
            "requires_human_review": True,
            "matched_keywords": [],
            "confidence_score": 0.40,
            "explanation": "Mail belirli bir kategoriyle güçlü şekilde eşleşmediği için manuel inceleme önerildi.",
        }

    return best_result