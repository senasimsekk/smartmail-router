import re

from app.services.classification_service import normalize_text
from app.services.preprocessing_service import build_classification_text, clean_email_body


def find_first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return match.group(0).strip()

    return None


def find_all_matches(pattern: str, text: str) -> list[str]:
    matches = re.findall(pattern, text, re.IGNORECASE)

    cleaned_matches = []

    for match in matches:
        if isinstance(match, tuple):
            value = " ".join(part for part in match if part)
        else:
            value = match

        value = value.strip()

        if value and value not in cleaned_matches:
            cleaned_matches.append(value)

    return cleaned_matches


def extract_sender_name(email: dict) -> str | None:
    sender = email.get("sender", "")

    if not sender:
        return None

    if "@" not in sender:
        return sender

    name_part = sender.split("@")[0]
    name_part = name_part.replace(".", " ")
    name_part = name_part.replace("_", " ")
    name_part = name_part.replace("-", " ")

    return name_part.title()


def extract_company_or_institution(text: str) -> str | None:
    company_patterns = [
        r"\b[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*(?:\s+[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*){0,5}\s+A\.Ş\.",
        r"\b[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*(?:\s+[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*){0,5}\s+Ltd\. Şti\.",
        r"\b[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*(?:\s+[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*){0,5}\s+Üniversitesi",
        r"\b[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*(?:\s+[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*){0,5}\s+Bakanlığı",
        r"\b[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*(?:\s+[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*){0,5}\s+Müdürlüğü",
        r"\b[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*(?:\s+[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*){0,5}\s+Kurumu",
        r"\b[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*(?:\s+[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*){0,5}\s+Derneği",
        r"\b[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*(?:\s+[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9]*){0,5}\s+Vakfı",
    ]

    for pattern in company_patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(0).strip()

    return None

    for pattern in company_patterns:
        match = find_first_match(pattern, text)

        if match:
            return match

    return None


def extract_complained_party(text: str) -> str | None:
    patterns = [
        r"(?:şikayet edilen|sikayet edilen|şikâyet edilen)\s*(?:taraf|firma|kurum)?[:\s-]+([A-Za-zÇĞİÖŞÜçğıöşü0-9\s\.]+)",
        r"([A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9\s]+ A\.Ş\.)\s+hakkında\s+şikayet",
        r"([A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9\s]+ Ltd\. Şti\.)\s+hakkında\s+şikayet",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return match.group(1).strip()

    return None


def extract_requested_action(normalized_text: str, classification: dict) -> str | None:
    if "silinmesini talep" in normalized_text or "verilerimin silinmesi" in normalized_text:
        return "Kişisel verilerin silinmesi talebi"

    if "bilgi talep" in normalized_text or "bilgi edinme" in normalized_text:
        return "Bilgi talebi"

    if "sikayet" in normalized_text:
        return "Şikayet incelemesi"

    if "ihbar" in normalized_text:
        return "İhbar incelemesi"

    if "teklif" in normalized_text or "ihale" in normalized_text:
        return "Satın alma sürecinin değerlendirilmesi"

    if "randevu" in normalized_text or "toplanti" in normalized_text or "gorusme" in normalized_text:
        return "Toplantı veya görüşme talebi"

    if "tebligat" in normalized_text or "mahkeme" in normalized_text or "dava" in normalized_text:
        return "Hukuki evrak kaydı ve inceleme"

    if "fatura" in normalized_text or "odeme" in normalized_text:
        return "Fatura veya ödeme işleminin incelenmesi"

    if classification["category"] == "Teknik Destek":
        return "Teknik destek talebinin incelenmesi"

    if classification["category"] == "Basın Talebi":
        return "Basın talebinin değerlendirilmesi"

    if classification["category"] == "İnsan Kaynakları":
        return "İnsan kaynakları sürecinin değerlendirilmesi"

    return None


def detect_confidentiality_level(normalized_text: str, classification: dict) -> str:
    if classification["category"] in ["KVKK Başvurusu", "Hukuki Tebligat", "İhbar"]:
        return "Gizli"

    sensitive_keywords = [
        "tc kimlik",
        "kimlik numarasi",
        "iban",
        "vergi no",
        "adres",
        "telefon",
        "saglik bilgisi",
        "kisisel veri",
        "veri ihlali",
        "mahkeme",
        "dava",
        "tebligat",
        "kep",
        "uyap",
    ]

    if any(keyword in normalized_text for keyword in sensitive_keywords):
        return "Gizli"

    if classification.get("requires_human_review"):
        return "Kurum içi"

    return "Normal"


def extract_main_topic(email: dict, classification: dict) -> str:
    subject = email.get("subject", "")

    if subject:
        return subject

    return classification["category"]


def extract_information_from_text(email: dict, classification: dict) -> dict:
    body = clean_email_body(email.get("body", ""))
    full_text = build_classification_text(email)
    normalized_text = normalize_text(full_text)

    email_addresses = find_all_matches(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        full_text,
    )

    phone_numbers = find_all_matches(
        r"(?:\+90\s?)?0?\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}",
        full_text,
    )

    tc_identity_numbers = find_all_matches(
        r"\b[1-9][0-9]{10}\b",
        full_text,
    )

    tax_numbers = find_all_matches(
        r"\b[0-9]{10}\b",
        full_text,
    )

    tax_numbers = [
        tax_number
        for tax_number in tax_numbers
        if tax_number not in tc_identity_numbers
    ]

    file_numbers = find_all_matches(
        r"\b20\d{2}[-/][0-9]{1,3}[-/][0-9]{1,5}\b",
        full_text,
    )

    application_numbers = find_all_matches(
    r"\b(?:başvuru|basvuru)\s*(?:no|numarası|numarasi)[:\s-]+[A-Za-z0-9-/]+\b",
    full_text,
  )

    decision_numbers = find_all_matches(
        r"\b(?:karar)\s*(?:no|numarası|numarasi)?[:\s-]*[A-Za-z0-9-/]+\b",
        full_text,
    )

    dates = find_all_matches(
        r"\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b",
        full_text,
    )

    money_amounts = find_all_matches(
        r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s?(?:TL|₺|TRY)\b",
        full_text,
    )

    mevzuat_references = find_all_matches(
        r"\b(?:4054|6698|4982)\s*(?:sayılı|sayili)?\s*(?:kanun|mevzuat)?\b",
        full_text,
    )

    institution = extract_company_or_institution(full_text)
    complained_party = extract_complained_party(full_text)
    requested_action = extract_requested_action(normalized_text, classification)
    confidentiality_level = detect_confidentiality_level(normalized_text, classification)

    return {
        "sender_name": extract_sender_name(email),
        "sender_email": email.get("sender"),
        "sender_institution": institution,
        "email_addresses": email_addresses,
        "phone_numbers": phone_numbers,
        "tc_identity_numbers": tc_identity_numbers,
        "tax_numbers": tax_numbers,
        "file_numbers": file_numbers,
        "application_numbers": application_numbers,
        "decision_numbers": decision_numbers,
        "dates": dates,
        "related_legislation": mevzuat_references,
        "money_amounts": money_amounts,
        "company_or_institution": institution,
        "complained_party": complained_party,
        "main_topic": extract_main_topic(email, classification),
        "requested_action": requested_action,
        "attachment_names": email.get("attachment_names", []),
        "confidentiality_level": confidentiality_level,
    }


def extract_structured_information(email: dict, classification: dict) -> dict:
    extracted_information = extract_information_from_text(email, classification)

    return {
        "mail_type": classification["category"],
        "sender": extracted_information["sender_name"],
        "sender_email": extracted_information["sender_email"],
        "sender_institution": extracted_information["sender_institution"],
        "phone_numbers": extracted_information["phone_numbers"],
        "tc_identity_numbers": extracted_information["tc_identity_numbers"],
        "tax_numbers": extracted_information["tax_numbers"],
        "file_numbers": extracted_information["file_numbers"],
        "application_numbers": extracted_information["application_numbers"],
        "decision_numbers": extracted_information["decision_numbers"],
        "dates": extracted_information["dates"],
        "related_legislation": extracted_information["related_legislation"],
        "money_amounts": extracted_information["money_amounts"],
        "company_or_institution": extracted_information["company_or_institution"],
        "complained_party": extracted_information["complained_party"],
        "main_topic": extracted_information["main_topic"],
        "requested_action": extracted_information["requested_action"],
        "attachment_names": extracted_information["attachment_names"],
        "confidentiality_level": extracted_information["confidentiality_level"],
        "priority": classification["priority"],
        "needs_human_review": classification["requires_human_review"],
        "suggested_department": classification["department"],
        "confidence_score": classification["confidence_score"],
    }