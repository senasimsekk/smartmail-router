from app.services.classification_service import normalize_text


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def get_file_extension(filename: str) -> str:
    if "." not in filename:
        return "unknown"

    return filename.rsplit(".", 1)[1].lower()


def detect_attachment_file_type(filename: str) -> str:
    extension = get_file_extension(filename)

    if extension == "pdf":
        return "PDF"

    if extension in ["doc", "docx"]:
        return "Word Document"

    if extension in ["xls", "xlsx", "csv"]:
        return "Spreadsheet"

    if extension in ["ppt", "pptx"]:
        return "PowerPoint"

    if extension in ["jpg", "jpeg", "png", "tiff", "bmp", "webp"]:
        return "Image / Scanned Document"

    if extension in ["zip", "rar", "7z"]:
        return "Compressed Archive"

    if extension in ["p7s", "asice", "mht"]:
        return "Signed / Official Document"

    return "Unknown"


def detect_file_security_status(filename: str, file_size: int | None = None) -> dict:
    extension = get_file_extension(filename)
    normalized_filename = normalize_text(filename)
    warnings = []

    if extension in ["exe", "bat", "cmd", "js", "vbs", "scr", "msi"]:
        warnings.append("Çalıştırılabilir dosya türü güvenlik riski oluşturabilir.")

    if extension in ["zip", "rar", "7z"]:
        warnings.append("Arşiv dosyası açılmadan önce güvenlik taramasından geçirilmelidir.")

    if contains_any(normalized_filename, ["sifreli", "encrypted", "parola", "password"]):
        warnings.append("Dosya şifreli olabilir; otomatik metin çıkarma sınırlı kalabilir.")

    if file_size is not None and file_size > 10 * 1024 * 1024:
        warnings.append("Dosya boyutu 10 MB üzerinde; manuel kontrol önerilir.")

    return {
        "scan_status": "MVP simülasyonu",
        "malware_risk": "Şüpheli" if warnings else "Düşük",
        "is_encrypted": contains_any(
            normalized_filename,
            ["sifreli", "encrypted", "parola", "password"],
        ),
        "file_size_warning": file_size is not None and file_size > 10 * 1024 * 1024,
        "warnings": warnings or ["Bilinen riskli dosya işareti tespit edilmedi."],
    }


def detect_personal_data_indicators(text: str) -> dict:
    normalized_text = normalize_text(text)
    indicators = []

    indicator_keywords = {
        "T.C. kimlik/vergi no": ["tc", "tckn", "kimlik", "vergi no", "vergi"],
        "Telefon": ["telefon", "gsm", "cep", "+90"],
        "Adres": ["adres", "mahalle", "sokak", "cadde"],
        "Finansal bilgi": ["iban", "hesap", "dekont", "odeme", "fatura"],
        "Sağlık bilgisi": ["saglik", "rapor", "hastane"],
        "İmza/kimlik görseli": ["imza", "kimlik fotokopisi", "nufus"],
    }

    for label, keywords in indicator_keywords.items():
        if contains_any(normalized_text, [normalize_text(keyword) for keyword in keywords]):
            indicators.append(label)

    return {
        "contains_personal_data": len(indicators) > 0,
        "indicators": indicators,
    }


def extract_attachment_entities(filename: str, extracted_text: str = "") -> dict:
    combined_text = f"{filename} {extracted_text}"
    normalized_text = normalize_text(combined_text)

    topic = "Belirlenemedi"

    if contains_any(normalized_text, ["tebligat", "mahkeme", "dava", "uyap", "kep"]):
        topic = "Hukuki evrak"
    elif contains_any(normalized_text, ["kvkk", "kisisel veri", "kimlik"]):
        topic = "KVKK / kişisel veri"
    elif contains_any(normalized_text, ["fatura", "odeme", "dekont", "iban"]):
        topic = "Mali belge"
    elif contains_any(normalized_text, ["sikayet", "ihbar", "basvuru"]):
        topic = "Başvuru / şikayet"

    dates = []
    file_numbers = []

    import re

    dates.extend(re.findall(r"\b\d{2}[./-]\d{2}[./-]\d{4}\b", combined_text))
    file_numbers.extend(
        re.findall(r"(?<!\d)20\d{2}-\d{1,3}-\d{3,6}(?!\d)", combined_text)
    )

    return {
        "topic": topic,
        "dates": sorted(set(dates)),
        "file_numbers": sorted(set(file_numbers)),
    }


def detect_ocr_requirement(filename: str) -> dict:
    extension = get_file_extension(filename)
    normalized_filename = normalize_text(filename)

    if extension in ["jpg", "jpeg", "png", "tiff", "bmp", "webp"]:
        return {
            "ocr_required": True,
            "reason": "Görsel dosyalarındaki metni okuyabilmek için OCR gerekir.",
        }

    if extension == "pdf" and contains_any(
        normalized_filename,
        ["tarama", "scan", "scanned", "kimlik", "imza", "dilekce"],
    ):
        return {
            "ocr_required": True,
            "reason": "Dosya adı taranmış belge veya görsel içerikli PDF olabileceğini gösteriyor.",
        }

    if extension == "pdf":
        return {
            "ocr_required": False,
            "reason": "PDF dosyası için önce normal metin çıkarma denenebilir.",
        }

    return {
        "ocr_required": False,
        "reason": "Bu dosya türü için ilk aşamada OCR gerekli görülmedi.",
    }


def detect_attachment_risk(filename: str, classification: dict) -> dict:
    normalized_filename = normalize_text(filename)

    risk_level = "Düşük"
    risk_reasons = []

    if contains_any(
        normalized_filename,
        [
            "tebligat",
            "mahkeme",
            "dava",
            "uyap",
            "kep",
            "icra",
            "dilekce",
        ],
    ):
        risk_level = "Kritik"
        risk_reasons.append("Dosya adı hukuki veya resmi evrak niteliği taşıyor.")

    if contains_any(
        normalized_filename,
        [
            "kvkk",
            "kisisel",
            "kimlik",
            "tc",
            "veri",
            "imza",
            "adres",
            "saglik",
            "iban",
        ],
    ):
        if risk_level != "Kritik":
            risk_level = "Yüksek"

        risk_reasons.append("Dosya adı kişisel veya hassas veri içerebileceğini gösteriyor.")

    if contains_any(
        normalized_filename,
        [
            "fatura",
            "odeme",
            "makbuz",
            "dekont",
            "hesap",
        ],
    ):
        if risk_level == "Düşük":
            risk_level = "Orta"

        risk_reasons.append("Dosya mali bilgi veya ödeme bilgisi içerebilir.")

    if contains_any(
        normalized_filename,
        [
            "sikayet",
            "ihbar",
            "basvuru",
            "basvuru_formu",
        ],
    ):
        if risk_level == "Düşük":
            risk_level = "Orta"

        risk_reasons.append("Dosya başvuru, şikayet veya ihbar içeriği taşıyabilir.")

    if classification["category"] in ["Hukuki Tebligat", "İhbar"]:
        risk_level = "Kritik"
        risk_reasons.append("Mailin kategorisi kritik olduğu için ek dosya da kritik kabul edildi.")

    if classification["category"] == "KVKK Başvurusu":
        if risk_level != "Kritik":
            risk_level = "Yüksek"

        risk_reasons.append("KVKK başvurusuna ait ekler kişisel veri içerebilir.")

    if not risk_reasons:
        risk_reasons.append("Dosya adından belirgin bir kritik risk tespit edilmedi.")

    return {
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
    }


def suggest_attachment_action(
    filename: str,
    file_type: str,
    risk_analysis: dict,
    ocr_analysis: dict,
) -> dict:
    normalized_filename = normalize_text(filename)

    requires_human_review = False
    requires_record = False
    suggested_action = "Ek dosya standart kontrol sürecinden geçirilebilir."

    if risk_analysis["risk_level"] in ["Kritik", "Yüksek"]:
        requires_human_review = True
        suggested_action = "Ek dosya insan onayı ile incelenmeli."

    if contains_any(
        normalized_filename,
        [
            "tebligat",
            "mahkeme",
            "dava",
            "kep",
            "uyap",
            "dilekce",
            "basvuru",
        ],
    ):
        requires_record = True
        suggested_action = "Ek dosya evrak/talep kaydıyla ilişkilendirilmeli."

    if file_type == "Compressed Archive":
        requires_human_review = True
        suggested_action = "Sıkıştırılmış dosya güvenlik kontrolünden geçirilmeden işlenmemeli."

    if ocr_analysis["ocr_required"]:
        suggested_action = "OCR ile metin çıkarıldıktan sonra sınıflandırma tekrar değerlendirilmelidir."

    return {
        "requires_human_review": requires_human_review,
        "requires_record": requires_record,
        "suggested_action": suggested_action,
    }


def analyze_single_attachment(
    filename: str,
    classification: dict,
    extracted_text: str = "",
    file_size: int | None = None,
) -> dict:
    file_type = detect_attachment_file_type(filename)
    ocr_analysis = detect_ocr_requirement(filename)
    risk_analysis = detect_attachment_risk(filename, classification)
    security_analysis = detect_file_security_status(filename, file_size)
    personal_data_analysis = detect_personal_data_indicators(
        f"{filename} {extracted_text}"
    )
    entity_analysis = extract_attachment_entities(filename, extracted_text)

    action_analysis = suggest_attachment_action(
        filename=filename,
        file_type=file_type,
        risk_analysis=risk_analysis,
        ocr_analysis=ocr_analysis,
    )

    return {
        "filename": filename,
        "file_extension": get_file_extension(filename),
        "file_type": file_type,
        "text_extraction_status": "Metin çıkarıldı" if extracted_text else "Metin bekleniyor",
        "ocr_required": ocr_analysis["ocr_required"],
        "ocr_reason": ocr_analysis["reason"],
        "security_scan_status": security_analysis["scan_status"],
        "malware_risk": security_analysis["malware_risk"],
        "is_encrypted": security_analysis["is_encrypted"],
        "file_size_warning": security_analysis["file_size_warning"],
        "security_warnings": security_analysis["warnings"],
        "contains_personal_data": personal_data_analysis["contains_personal_data"],
        "personal_data_indicators": personal_data_analysis["indicators"],
        "extracted_topic": entity_analysis["topic"],
        "extracted_dates": entity_analysis["dates"],
        "extracted_file_numbers": entity_analysis["file_numbers"],
        "risk_level": risk_analysis["risk_level"],
        "risk_reasons": risk_analysis["risk_reasons"],
        "requires_human_review": action_analysis["requires_human_review"],
        "requires_record": action_analysis["requires_record"],
        "suggested_action": action_analysis["suggested_action"],
    }


def analyze_attachments(email: dict, classification: dict) -> dict:
    attachment_names = email.get("attachment_names", [])
    attachment_texts = {
        item.get("filename"): item
        for item in email.get("attachment_texts", [])
        if item.get("filename")
    }

    if not attachment_names:
        return {
            "has_attachments": False,
            "attachment_count": 0,
            "attachments": [],
            "overall_risk_level": "Düşük",
            "requires_human_review": False,
            "requires_record": False,
            "summary": "Mailde ek dosya bulunmuyor.",
        }

    attachments = [
        analyze_single_attachment(
            filename,
            classification,
            extracted_text=attachment_texts.get(filename, {}).get("extracted_text", ""),
        )
        for filename in attachment_names
    ]

    overall_risk_level = "Düşük"

    if any(attachment["risk_level"] == "Kritik" for attachment in attachments):
        overall_risk_level = "Kritik"
    elif any(attachment["risk_level"] == "Yüksek" for attachment in attachments):
        overall_risk_level = "Yüksek"
    elif any(attachment["risk_level"] == "Orta" for attachment in attachments):
        overall_risk_level = "Orta"

    requires_human_review = any(
        attachment["requires_human_review"]
        for attachment in attachments
    )

    requires_record = any(
        attachment["requires_record"]
        for attachment in attachments
    )

    return {
        "has_attachments": True,
        "attachment_count": len(attachments),
        "attachments": attachments,
        "overall_risk_level": overall_risk_level,
        "requires_human_review": requires_human_review,
        "requires_record": requires_record,
        "summary": (
            f"Mailde {len(attachments)} ek dosya bulundu. "
            f"Genel ek riski: {overall_risk_level}."
        ),
    }
