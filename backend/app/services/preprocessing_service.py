import re
from html import unescape


SIGNATURE_MARKERS = [
    "iyi çalışmalar",
    "iyi calismalar",
    "saygılarımla",
    "saygilarimla",
    "saygılarımızla",
    "saygilarimizla",
    "teşekkürler",
    "tesekkurler",
    "best regards",
    "regards",
]


def remove_html_tags(text: str) -> str:
    """
    HTML içeren mail gövdesini düz metne çevirir.
    Örneğin <p>Merhaba</p> -> Merhaba
    """

    if not text:
        return ""

    text = unescape(text)

    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)

    return text


def normalize_whitespace(text: str) -> str:
    """
    Fazla boşluk, tab ve satır boşluklarını temizler.
    """

    if not text:
        return ""

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)

    return text.strip()


def remove_signature(text: str) -> str:
    """
    Mailin sonunda yer alan imza benzeri ifadeleri temizler.
    Örneğin:
    İyi çalışmalar,
    Ahmet Yılmaz
    """

    if not text:
        return ""

    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        normalized_line = line.strip().lower()

        if any(normalized_line.startswith(marker) for marker in SIGNATURE_MARKERS):
            break

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def clean_email_body(body: str) -> str:
    """
    Mail gövdesini sınıflandırmaya hazır hale getirir.
    """

    text = remove_html_tags(body)
    text = normalize_whitespace(text)
    text = remove_signature(text)
    text = normalize_whitespace(text)

    return text


def build_classification_text(email: dict) -> str:
  

    subject = email.get("subject", "")
    body = email.get("body", "")

    cleaned_body = clean_email_body(body)
    attachment_names = email.get("attachment_names", [])

    if attachment_names:
        attachment_text = " ".join(attachment_names)
    else:
        attachment_text = ""
    return f"{subject} {cleaned_body}".strip()


def preprocess_email(email: dict) -> dict:
    

    subject = email.get("subject", "")
    body = email.get("body", "")

    cleaned_body = clean_email_body(body)
    classification_text = build_classification_text(email)

    return {
        "subject": subject,
        "original_body": body,
        "cleaned_body": cleaned_body,
        "classification_text": classification_text,
    }