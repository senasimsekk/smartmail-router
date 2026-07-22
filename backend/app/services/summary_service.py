import math
import re
from collections import Counter

from app.services.classification_service import CLASSIFICATION_RULES, normalize_text
from app.services.information_extraction_service import extract_information_from_text
from app.services.preprocessing_service import build_classification_text, clean_email_body


SUMMARY_STOP_WORDS = {
    "acaba",
    "ama",
    "ancak",
    "ben",
    "bir",
    "bu",
    "da",
    "de",
    "diye",
    "icin",
    "ile",
    "ise",
    "mail",
    "merhaba",
    "olarak",
    "saygilarimla",
    "sunulmustur",
    "ve",
    "veya",
}
LARGE_ATTACHMENT_TEXT_THRESHOLD = 1200
ATTACHMENT_CHUNK_CHAR_LIMIT = 900
MAX_LARGE_ATTACHMENT_CHUNK_SUMMARIES = 3


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


def get_category_keywords(category: str) -> list[str]:
    for rule in CLASSIFICATION_RULES:
        if rule["category"] == category:
            return rule["keywords"]

    return []


def tokenize_summary_text(text: str) -> list[str]:
    normalized = normalize_text(text)
    tokens = re.findall(r"[a-z0-9]{3,}", normalized)

    return [token for token in tokens if token not in SUMMARY_STOP_WORDS]


def split_summary_sentences(text: str) -> list[str]:
    cleaned = normalize_whitespace(text)

    if not cleaned:
        return []

    pieces = re.split(r"(?<=[.!?])(?<!\d\.)\s+|\n+", cleaned)

    return [
        piece.strip(" -")
        for piece in pieces
        if 20 <= len(piece.strip()) <= 320
    ]


def get_attachment_text_entries(email: dict) -> list[dict]:
    entries = []

    for index, item in enumerate(email.get("attachment_texts", []) or [], start=1):
        if not isinstance(item, dict):
            continue

        extracted_text = normalize_whitespace(item.get("extracted_text", ""))

        if not extracted_text:
            continue

        entries.append(
            {
                "filename": item.get("filename") or f"Ek {index}",
                "text": extracted_text,
                "is_large": len(extracted_text) >= LARGE_ATTACHMENT_TEXT_THRESHOLD,
            }
        )

    return entries


def chunk_sentences_by_length(sentences: list[str], max_chars: int) -> list[str]:
    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence)

        if current_chunk and current_length + sentence_length > max_chars:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(sentence)
        current_length += sentence_length + 1

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def build_attachment_sentence_candidates(attachment: dict) -> list[dict]:
    sentences = split_summary_sentences(attachment["text"])

    if not sentences:
        return []

    if not attachment["is_large"]:
        return [
            {
                "source": "attachment",
                "filename": attachment["filename"],
                "sentence": sentence,
                "chunk_index": None,
                "chunk_count": 1,
                "is_large_attachment": False,
            }
            for sentence in sentences
        ]

    chunks = chunk_sentences_by_length(sentences, ATTACHMENT_CHUNK_CHAR_LIMIT)
    candidates = []

    for chunk_index, chunk in enumerate(chunks, start=1):
        for sentence in split_summary_sentences(chunk):
            candidates.append(
                {
                    "source": "attachment",
                    "filename": attachment["filename"],
                    "sentence": sentence,
                    "chunk_index": chunk_index,
                    "chunk_count": len(chunks),
                    "is_large_attachment": True,
                }
            )

    return candidates


def build_sentence_candidates(email: dict) -> list[dict]:
    candidates = [
        {
            "source": "mail",
            "filename": "",
            "sentence": sentence,
            "chunk_index": None,
            "chunk_count": 1,
            "is_large_attachment": False,
        }
        for sentence in split_summary_sentences(clean_email_body(email.get("body", "")))
    ]

    for attachment in get_attachment_text_entries(email):
        candidates.extend(build_attachment_sentence_candidates(attachment))

    return candidates


def build_idf_weights(candidates: list[dict]) -> dict[str, float]:
    documents = [set(tokenize_summary_text(candidate["sentence"])) for candidate in candidates]
    document_count = len(documents)
    document_frequencies = Counter(
        token
        for document in documents
        for token in document
    )

    return {
        token: math.log((1 + document_count) / (1 + frequency)) + 1
        for token, frequency in document_frequencies.items()
    }


def score_candidate(
    candidate: dict,
    idf_weights: dict[str, float],
    keyword_terms: set[str],
    index: int,
) -> float:
    tokens = tokenize_summary_text(candidate["sentence"])

    if not tokens:
        return 0

    token_counts = Counter(tokens)
    tfidf_score = sum(
        count * idf_weights.get(token, 1)
        for token, count in token_counts.items()
    )
    score = tfidf_score / math.sqrt(len(tokens))
    normalized_sentence = normalize_text(candidate["sentence"])

    if keyword_terms & set(tokens):
        score += 2.5

    if re.search(r"\b\d{2}[./-]\d{2}[./-]\d{4}\b|\b20\d{2}\b", candidate["sentence"]):
        score += 1

    if re.search(r"\b(?:RK|E|K|UYAP|KEP)[-/:\s]*\d", candidate["sentence"], flags=re.IGNORECASE):
        score += 1

    if contains_any(normalized_sentence, ["talep", "basvuru", "sikayet", "ihbar", "tebligat"]):
        score += 1

    if candidate["source"] == "attachment":
        score += 0.8

    if index == 0:
        score += 0.4

    return score


def select_relevant_sentences(email: dict, classification: dict, max_sentences: int = 2) -> list[dict]:
    candidates = build_sentence_candidates(email)

    if not candidates:
        return []

    keyword_text = " ".join(
        [
            classification.get("category", ""),
            classification.get("department", ""),
            " ".join(classification.get("matched_keywords", []) or []),
            " ".join(get_category_keywords(classification.get("category", ""))),
        ]
    )
    keyword_terms = set(tokenize_summary_text(keyword_text))
    idf_weights = build_idf_weights(candidates)
    scored_candidates = [
        {
            **candidate,
            "score": score_candidate(candidate, idf_weights, keyword_terms, index),
        }
        for index, candidate in enumerate(candidates)
    ]
    selected = []
    seen_sentences = set()
    used_large_chunks = set()

    for candidate in sorted(scored_candidates, key=lambda item: item["score"], reverse=True):
        normalized_sentence = normalize_text(candidate["sentence"])
        large_chunk_key = (
            candidate["filename"],
            candidate["chunk_index"],
        )

        if normalized_sentence in seen_sentences:
            continue

        if (
            candidate.get("is_large_attachment")
            and large_chunk_key in used_large_chunks
            and len(selected) < max_sentences
        ):
            continue

        selected.append(candidate)
        seen_sentences.add(normalized_sentence)

        if candidate.get("is_large_attachment"):
            used_large_chunks.add(large_chunk_key)

        if len(selected) == max_sentences:
            break

    return selected


def build_large_attachment_note(selected_sentences: list[dict]) -> str:
    large_attachment_counts = {}

    for item in selected_sentences:
        if item.get("is_large_attachment"):
            large_attachment_counts[item["filename"]] = item["chunk_count"]

    if not large_attachment_counts:
        return ""

    notes = [
        f"{filename} {chunk_count} parçaya ayrılarak tarandı"
        for filename, chunk_count in large_attachment_counts.items()
    ]

    return f"Büyük ek metni parça bazlı özetlendi: {'; '.join(notes)}."


def build_context_sentence(selected_sentences: list[dict]) -> str:
    if not selected_sentences:
        return ""

    fragments = []

    for item in selected_sentences:
        sentence = shorten_text(normalize_whitespace(item["sentence"]), 150)

        if item["source"] == "attachment":
            chunk_label = (
                f" parça {item['chunk_index']}"
                if item.get("is_large_attachment") and item.get("chunk_index")
                else ""
            )
            fragments.append(f"{item['filename']}{chunk_label} içinde \"{sentence}\"")
        else:
            fragments.append(f"mail gövdesinde \"{sentence}\"")

    return f"Bağlam sinyali: {'; '.join(fragments)}."


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
    selected_sentences = select_relevant_sentences(
        email,
        classification,
        max_sentences=MAX_LARGE_ATTACHMENT_CHUNK_SUMMARIES,
    )
    large_attachment_note = build_large_attachment_note(selected_sentences)
    context_sentence = build_context_sentence(selected_sentences)

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

    if large_attachment_note:
        summary_parts.append(large_attachment_note)

    if context_sentence:
        summary_parts.append(context_sentence)

    if message_signal:
        summary_parts.append(message_signal)

    summary_parts.append(
        f"Önerilen işlem: {department} tarafından {priority.lower()} öncelikle değerlendirilmesi."
    )

    contextual_summary = " ".join(summary_parts)

    if category in [
        "KVKK Başvurusu",
        "Teknik Destek",
        "Basın Talebi",
        "Satın Alma",
        "Hukuki Tebligat",
        "Şikayet",
        "İhbar",
        "Bilgi Edinme",
        "İnsan Kaynakları",
        "Evrak Kayıt",
    ]:
        return contextual_summary

    if category in ["Fatura / Ödeme", "Fatura/Ödeme"]:
        return contextual_summary

    if contains_any(normalized_text, ["toplanti", "randevu", "gorusme"]):
        return contextual_summary

    return (
        f"{contextual_summary} "
        f"İçerik özeti: {shorten_text(cleaned_body)}"
    )
