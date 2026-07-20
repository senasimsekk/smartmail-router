import re
from html import unescape
from typing import Any


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
    "kolay gelsin",
]

FOOTER_MARKERS = [
    "bu e-posta ve ekleri",
    "bu mesaj ve ekleri",
    "bu ileti ve ekleri",
    "bu e-posta gizlidir",
    "bu mesaj gizlidir",
    "the information contained in this e-mail",
    "this e-mail and any attachments",
    "unsubscribe",
    "abonelikten çık",
]

REPLY_MARKERS = [
    r"^-{2,}\s*original message\s*-{2,}$",
    r"^from:\s+.+$",
    r"^kimden:\s+.+$",
    r"^gönderen:\s+.+$",
    r"^sent:\s+.+$",
    r"^tarih:\s+.+$",
    r"^on .+ wrote:$",
    r"^.+ tarihinde .+ yazdı:$",
]

HEADER_PATTERNS = {
    "sender": [r"^(?:from|kimden|gönderen)\s*:\s*(.+)$"],
    "recipients": [r"^(?:to|kime|alıcılar)\s*:\s*(.+)$"],
    "cc": [r"^(?:cc|bilgi)\s*:\s*(.+)$"],
    "subject": [r"^(?:subject|konu)\s*:\s*(.+)$"],
    "date": [r"^(?:date|sent|tarih|gönderilme tarihi)\s*:\s*(.+)$"],
}

MOJIBAKE_REPLACEMENTS = {
    "Ä°": "İ",
    "Ä±": "ı",
    "Ã§": "ç",
    "Ã‡": "Ç",
    "ÄŸ": "ğ",
    "Äž": "Ğ",
    "Ã¶": "ö",
    "Ã–": "Ö",
    "ÅŸ": "ş",
    "Åž": "Ş",
    "Ã¼": "ü",
    "Ãœ": "Ü",
    "â€™": "'",
    "â€œ": '"',
    "â€": '"',
    "â€“": "-",
    "â€”": "-",
}

ATTACHMENT_PATTERN = re.compile(
    r"[\wçğıöşüÇĞİÖŞÜ().\- ]+\.(?:pdf|docx?|xlsx?|csv|pptx?|jpe?g|png|tiff?|bmp|webp|zip|rar|7z|p7s|asice|mht|txt)",
    re.IGNORECASE,
)


def fix_broken_characters(text: str) -> str:
    if not text:
        return ""

    for broken, fixed in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(broken, fixed)

    return text


def normalize_for_match(text: str) -> str:
    return fix_broken_characters(text or "").lower().replace("i̇", "i")


def remove_html_tags(text: str) -> str:
    if not text:
        return ""

    text = unescape(text)
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(?:p|div|li|tr|h[1-6])\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)

    return text


def normalize_whitespace(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines()]


def is_signature_line(line: str) -> bool:
    normalized_line = normalize_for_match(line.strip())
    return any(normalized_line.startswith(marker) for marker in SIGNATURE_MARKERS)


def is_footer_line(line: str) -> bool:
    normalized_line = normalize_for_match(line.strip())
    return any(marker in normalized_line for marker in FOOTER_MARKERS)


def is_reply_marker(line: str) -> bool:
    normalized_line = normalize_for_match(line.strip())
    return any(re.match(pattern, normalized_line) for pattern in REPLY_MARKERS)


def split_reply_chain(text: str) -> dict[str, Any]:
    lines = split_lines(text)
    main_lines: list[str] = []
    reply_lines: list[str] = []
    in_reply = False

    for line in lines:
        if is_reply_marker(line):
            in_reply = True

        if in_reply:
            reply_lines.append(line)
        else:
            main_lines.append(line)

    previous_replies = []
    reply_text = normalize_whitespace("\n".join(reply_lines))

    if reply_text:
        blocks = [
            normalize_whitespace(block)
            for block in re.split(r"\n(?=(?:From|Kimden|Gönderen|On .+ wrote|.+ tarihinde .+ yazdı):?)", reply_text)
            if normalize_whitespace(block)
        ]
        previous_replies = blocks or [reply_text]

    return {
        "main_message": normalize_whitespace("\n".join(main_lines)),
        "previous_replies": previous_replies,
    }


def extract_signature(text: str) -> dict[str, str]:
    lines = split_lines(text)
    message_lines: list[str] = []
    signature_lines: list[str] = []
    in_signature = False

    for line in lines:
        if is_signature_line(line):
            in_signature = True

        if in_signature:
            signature_lines.append(line)
        else:
            message_lines.append(line)

    return {
        "message_without_signature": normalize_whitespace("\n".join(message_lines)),
        "signature": normalize_whitespace("\n".join(signature_lines)),
    }


def remove_signature(text: str) -> str:
    return extract_signature(text)["message_without_signature"]


def extract_footer(text: str) -> dict[str, str]:
    lines = split_lines(text)
    content_lines: list[str] = []
    footer_lines: list[str] = []
    in_footer = False

    for line in lines:
        if is_footer_line(line):
            in_footer = True

        if in_footer:
            footer_lines.append(line)
        else:
            content_lines.append(line)

    return {
        "body_without_footer": normalize_whitespace("\n".join(content_lines)),
        "footer": normalize_whitespace("\n".join(footer_lines)),
    }


def extract_header_fields(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "sender": None,
        "recipients": [],
        "cc": [],
        "subject": None,
        "date": None,
    }

    for line in split_lines(text):
        for field_name, patterns in HEADER_PATTERNS.items():
            for pattern in patterns:
                match = re.match(pattern, line, flags=re.IGNORECASE)

                if not match:
                    continue

                value = match.group(1).strip()

                if field_name in {"recipients", "cc"}:
                    fields[field_name] = split_address_list(value)
                else:
                    fields[field_name] = value

    return fields


def split_address_list(value: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"[;,]", value or "")
        if item.strip()
    ]


def extract_attachment_names_from_text(text: str) -> list[str]:
    matches = ATTACHMENT_PATTERN.findall(text or "")
    cleaned_names = []

    for match in matches:
        cleaned_name = re.sub(r"^(?:ek|ekte|dosya|attachment)[\s:.-]+", "", match.strip(), flags=re.IGNORECASE)
        cleaned_name = cleaned_name.strip(" .,:;")

        if cleaned_name and cleaned_name not in cleaned_names:
            cleaned_names.append(cleaned_name)

    return cleaned_names


def detect_language(text: str) -> str:
    normalized = (text or "").lower()
    turkish_score = len(re.findall(r"[çğıöşü]", normalized))
    turkish_score += sum(
        keyword in normalized
        for keyword in ["merhaba", "başvuru", "talep", "ekte", "saygılarımla", "kurum"]
    )
    english_score = sum(
        keyword in normalized
        for keyword in ["hello", "dear", "attached", "regards", "request", "please"]
    )

    if turkish_score > english_score and turkish_score > 0:
        return "Türkçe"

    if english_score > turkish_score and english_score > 0:
        return "İngilizce"

    return "Bilinmiyor"


def detect_spam_or_auto_reply(subject: str, sender: str, body: str) -> dict[str, Any]:
    normalized_text = " ".join([subject or "", sender or "", body or ""]).lower()
    auto_reply_keywords = [
        "otomatik cevap",
        "otomatik yanıt",
        "ofis dışında",
        "out of office",
        "auto reply",
        "automatic reply",
        "noreply",
        "no-reply",
    ]
    spam_keywords = [
        "unsubscribe",
        "abonelikten çık",
        "kampanya",
        "indirim",
        "reklam",
        "promotion",
        "newsletter",
        "spam",
    ]

    auto_reply_hits = [
        keyword for keyword in auto_reply_keywords if keyword in normalized_text
    ]
    spam_hits = [keyword for keyword in spam_keywords if keyword in normalized_text]

    return {
        "is_automatic_reply": bool(auto_reply_hits),
        "is_spam_like": bool(spam_hits),
        "detected_markers": auto_reply_hits + spam_hits,
    }


def prepare_plain_text(body: str) -> str:
    text = fix_broken_characters(body or "")
    text = remove_html_tags(text)
    text = normalize_whitespace(text)

    return text


def clean_email_body(body: str) -> str:
    preprocessed = preprocess_body(body)
    return preprocessed["cleaned_body"]


def preprocess_body(body: str) -> dict[str, Any]:
    plain_text = prepare_plain_text(body)
    reply_result = split_reply_chain(plain_text)
    footer_result = extract_footer(reply_result["main_message"])
    signature_result = extract_signature(footer_result["body_without_footer"])
    main_message = signature_result["message_without_signature"]

    return {
        "plain_text": plain_text,
        "main_message": main_message,
        "previous_replies": reply_result["previous_replies"],
        "signature": signature_result["signature"],
        "footer": footer_result["footer"],
        "cleaned_body": normalize_whitespace(main_message),
    }


def normalize_attachment_names(attachment_names: list[str] | None) -> list[str]:
    cleaned_names = []

    for attachment_name in attachment_names or []:
        if not attachment_name:
            continue

        cleaned_name = str(attachment_name).strip()

        if cleaned_name and cleaned_name not in cleaned_names:
            cleaned_names.append(cleaned_name)

    return cleaned_names


def build_classification_text(email: dict) -> str:
    subject = email.get("subject", "")
    body_result = preprocess_body(email.get("body", ""))
    attachment_names = normalize_attachment_names(email.get("attachment_names", []))
    body_attachment_names = extract_attachment_names_from_text(body_result["plain_text"])
    attachment_texts = email.get("attachment_texts", [])

    attachment_name_text = " ".join(attachment_names + body_attachment_names)
    extracted_attachment_text = " ".join(
        item.get("extracted_text", "")
        for item in attachment_texts
        if isinstance(item, dict)
    )

    return " ".join(
        part
        for part in [
            subject,
            body_result["cleaned_body"],
            attachment_name_text,
            extracted_attachment_text,
        ]
        if part
    ).strip()


def preprocess_email(email: dict) -> dict:
    subject = email.get("subject", "")
    sender = email.get("sender", "")
    body = email.get("body", "")
    body_result = preprocess_body(body)
    header_fields = extract_header_fields(body_result["plain_text"])
    stored_attachment_names = normalize_attachment_names(email.get("attachment_names", []))
    body_attachment_names = extract_attachment_names_from_text(body_result["plain_text"])
    attachment_names = normalize_attachment_names(
        stored_attachment_names + body_attachment_names
    )
    spam_result = detect_spam_or_auto_reply(subject, sender, body_result["plain_text"])
    classification_text = build_classification_text(
        {
            **email,
            "body": body,
            "attachment_names": attachment_names,
        }
    )

    return {
        "subject": subject,
        "sender": {
            "raw": sender,
            "parsed": header_fields["sender"] or sender,
        },
        "recipients": header_fields["recipients"],
        "cc": header_fields["cc"],
        "date": header_fields["date"],
        "original_body": body,
        "plain_text": body_result["plain_text"],
        "main_message": body_result["main_message"],
        "previous_replies": body_result["previous_replies"],
        "signature": body_result["signature"],
        "footer": body_result["footer"],
        "cleaned_body": body_result["cleaned_body"],
        "language": detect_language(body_result["plain_text"]),
        "spam_or_automatic": spam_result,
        "attachments": {
            "stored_names": stored_attachment_names,
            "detected_in_body": body_attachment_names,
            "all_names": attachment_names,
        },
        "classification_text": classification_text,
        "steps": [
            "Bozuk karakter düzeltme",
            "HTML'den düz metin çıkarma",
            "Cevap zinciri ayrıştırma",
            "İmza temizleme",
            "Footer temizleme",
            "Dil algılama",
            "Spam/otomatik cevap kontrolü",
            "Ek dosya ve gönderici bilgisi çıkarımı",
        ],
    }
