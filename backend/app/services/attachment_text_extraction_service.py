import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models.email import Email
from app.services.attachment_analysis_service import (
    detect_attachment_file_type,
    detect_file_security_status,
    detect_personal_data_indicators,
    extract_attachment_entities,
)
from app.services.email_db_service import email_to_dict
from app.services.system_log_service import create_system_log


UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
MAX_EXTRACTED_TEXT_LENGTH = 12000


def sanitize_filename(filename: str) -> str:
    safe_name = Path(filename or "attachment").name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)

    return safe_name or "attachment"


def get_extension(filename: str) -> str:
    if "." not in filename:
        return ""

    return filename.rsplit(".", 1)[1].lower()


def extract_text_from_pdf(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    page_texts = []

    for page in reader.pages:
        page_texts.append(page.extract_text() or "")

    return "\n".join(page_texts).strip()


def extract_text_from_docx(file_path: Path) -> str:
    document = Document(str(file_path))
    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    return "\n".join(paragraphs)


def extract_text_from_plain_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore").strip()


def build_attachment_extraction_metadata(
    filename: str,
    file_size: int,
    extracted_text: str,
) -> dict:
    security_analysis = detect_file_security_status(filename, file_size)
    personal_data_analysis = detect_personal_data_indicators(
        f"{filename} {extracted_text}"
    )
    entity_analysis = extract_attachment_entities(filename, extracted_text)

    return {
        "file_size": file_size,
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
    }


def extract_text_from_file(file_path: Path, filename: str) -> dict:
    extension = get_extension(filename)
    file_type = detect_attachment_file_type(filename)
    file_size = file_path.stat().st_size

    try:
        if extension == "pdf":
            extracted_text = extract_text_from_pdf(file_path)
        elif extension in ["docx"]:
            extracted_text = extract_text_from_docx(file_path)
        elif extension in ["txt", "csv"]:
            extracted_text = extract_text_from_plain_file(file_path)
        else:
            return {
                "filename": filename,
                "file_type": file_type,
                "status": "unsupported",
                "extracted_text": "",
                "character_count": 0,
                "warning": "Bu MVP sürümünde bu dosya türünden metin çıkarılmıyor.",
                **build_attachment_extraction_metadata(filename, file_size, ""),
            }

        if len(extracted_text) > MAX_EXTRACTED_TEXT_LENGTH:
            extracted_text = extracted_text[:MAX_EXTRACTED_TEXT_LENGTH].strip()

        status = "success" if extracted_text else "empty"
        warning = None if extracted_text else "Dosyadan okunabilir metin çıkarılamadı."

        return {
            "filename": filename,
            "file_type": file_type,
            "status": status,
            "extracted_text": extracted_text,
            "character_count": len(extracted_text),
            "warning": warning,
            **build_attachment_extraction_metadata(
                filename,
                file_size,
                extracted_text,
            ),
        }
    except Exception as exc:
        return {
            "filename": filename,
            "file_type": file_type,
            "status": "error",
            "extracted_text": "",
            "character_count": 0,
            "warning": f"Metin çıkarma sırasında hata oluştu: {exc}",
            **build_attachment_extraction_metadata(filename, file_size, ""),
        }


def save_attachment_and_extract_text(
    db: Session,
    email_id: int,
    filename: str,
    file_content: bytes,
    uploaded_by: str = "operator",
) -> dict | None:
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        return None

    safe_filename = sanitize_filename(filename)
    email_upload_dir = UPLOAD_DIR / str(email_id)
    email_upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = email_upload_dir / safe_filename
    file_path.write_bytes(file_content)

    extraction_result = extract_text_from_file(
        file_path=file_path,
        filename=safe_filename,
    )

    attachment_names = email.attachment_names or []
    attachment_texts = email.attachment_texts or []

    if safe_filename not in attachment_names:
        attachment_names.append(safe_filename)

    attachment_texts = [
        item
        for item in attachment_texts
        if item.get("filename") != safe_filename
    ]
    attachment_texts.append(extraction_result)

    email.has_attachment = True
    email.attachment_names = attachment_names
    email.attachment_texts = attachment_texts

    db.commit()
    db.refresh(email)

    log = create_system_log(
        db=db,
        email_id=email.id,
        action_type="ATTACHMENT_UPLOADED",
        action_detail="Attachment was uploaded and text extraction was attempted.",
        actor=uploaded_by,
        extra_data={
            "filename": safe_filename,
            "status": extraction_result["status"],
            "character_count": extraction_result["character_count"],
        },
    )

    return {
        "message": "Attachment uploaded and analyzed.",
        "email": email_to_dict(email),
        "attachment_text": extraction_result,
        "system_log": log,
    }
