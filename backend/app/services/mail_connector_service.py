import imaplib
import json
import os
import re
from dataclasses import dataclass, field
from email import policy
from email.header import decode_header, make_header
from email.parser import BytesParser
from email.utils import parseaddr
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parents[3]
SYNTHETIC_EMAILS_FILE = PROJECT_DIR / "data" / "synthetic_emails.json"

load_dotenv(PROJECT_DIR / "backend" / ".env")


@dataclass
class MailConnectorConfig:
    connector_id: str
    name: str
    source_type: str
    mode: str
    status: str
    source_mailbox: str
    capabilities: list[str] = field(default_factory=list)
    required_settings: list[str] = field(default_factory=list)
    next_step: str = ""


class MailConnector(Protocol):
    config: MailConnectorConfig

    def fetch_messages(self, limit: int) -> list[dict]:
        ...

    def test_connection(self) -> dict:
        ...


class SyntheticMailboxConnector:
    def __init__(
        self,
        source_mailbox: str = "webmaster@rekabet.gov.tr",
        dataset_path: Path = SYNTHETIC_EMAILS_FILE,
    ):
        self.dataset_path = dataset_path
        self.config = MailConnectorConfig(
            connector_id="synthetic_demo",
            name="Sentetik Webmaster Kutusu",
            source_type="E-posta arşivinden toplu aktarım",
            mode="Demo veri",
            status="ready",
            source_mailbox=source_mailbox,
            capabilities=[
                "webmaster@rekabet.gov.tr ortak kutusunu simüle eder",
                "Mail gövdesi ve ek adlarını standart formata taşır",
                "Tekrarlı e-posta kontrolüne uygun veri üretir",
            ],
            next_step="Gerçek hesap bilgileri geldiğinde aynı sözleşmeye IMAP/Gmail connector bağlanır.",
        )

    def load_messages(self) -> list[dict]:
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.dataset_path}")

        with open(self.dataset_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def fetch_messages(self, limit: int) -> list[dict]:
        messages = [
            normalize_connector_message(message, self.config.source_mailbox)
            for message in self.load_messages()
            if message.get("source_mailbox") == self.config.source_mailbox
        ]

        return messages[:limit]

    def test_connection(self) -> dict:
        messages = self.load_messages()
        available_count = sum(
            1
            for message in messages
            if message.get("source_mailbox") == self.config.source_mailbox
        )

        return {
            "connector_id": self.config.connector_id,
            "status": "ready",
            "message": "Sentetik posta kutusu okunabilir durumda.",
            "available_message_count": available_count,
        }


class PlannedMailConnector:
    def __init__(
        self,
        connector_id: str,
        name: str,
        source_type: str,
        source_mailbox: str,
        required_settings: list[str],
        next_step: str,
    ):
        self.config = MailConnectorConfig(
            connector_id=connector_id,
            name=name,
            source_type=source_type,
            mode="Canlı bağlantı hazırlığı",
            status="planned",
            source_mailbox=source_mailbox,
            capabilities=[
                "Gövde, başlık ve gönderen bilgisini standart mail formatına çevirir",
                "Ek dosya listesini metin çıkarma modülüne aktarır",
                "Başarısız bağlantı ve yetki hatalarını ingestion loglarına taşır",
            ],
            required_settings=required_settings,
            next_step=next_step,
        )

    def fetch_messages(self, limit: int) -> list[dict]:
        raise NotImplementedError(
            f"{self.config.name} için canlı bağlantı bilgileri henüz tanımlanmadı."
        )

    def test_connection(self) -> dict:
        return {
            "connector_id": self.config.connector_id,
            "status": "configuration_required",
            "message": "Canlı bağlantı için hesap ve yetki bilgileri gerekir.",
            "required_settings": self.config.required_settings,
        }


class ImapMailboxConnector:
    def __init__(
        self,
        connector_id: str,
        name: str,
        source_type: str,
        source_mailbox: str,
        default_host: str = "",
        default_port: int = 993,
    ):
        self.host = os.getenv("MAIL_HOST", default_host).strip()
        self.port = int(os.getenv("MAIL_PORT", str(default_port)))
        self.username = os.getenv("MAIL_USERNAME", "").strip()
        self.password = os.getenv("MAIL_PASSWORD", "").strip()
        self.folder = os.getenv("MAIL_FOLDER", "INBOX").strip() or "INBOX"
        self.use_ssl = os.getenv("MAIL_USE_SSL", "true").lower() != "false"
        effective_mailbox = self.username or source_mailbox
        is_configured = bool(self.host and self.username and self.password)

        self.config = MailConnectorConfig(
            connector_id=connector_id,
            name=name,
            source_type=source_type,
            mode="Canlı IMAP bağlantısı",
            status="ready" if is_configured else "configuration_required",
            source_mailbox=effective_mailbox,
            capabilities=[
                "Gelen kutusundaki gerçek e-postaları IMAP üzerinden okur",
                "Konu, gönderen, gövde ve ek dosya adlarını standart formata çevirir",
                "İçe aktarılan mailleri mevcut sınıflandırma hattına aktarır",
            ],
            required_settings=[
                "MAIL_HOST",
                "MAIL_PORT",
                "MAIL_USERNAME",
                "MAIL_PASSWORD",
                "MAIL_USE_SSL",
                "MAIL_FOLDER",
            ],
            next_step=(
                "backend/.env içindeki Gmail uygulama şifresiyle canlı posta "
                "kutusu senkronize edilir."
                if is_configured
                else "Gmail uygulama şifresi backend/.env içine eklenince connector hazır olur."
            ),
        )

    def _validate_configuration(self) -> None:
        missing_settings = []

        if not self.host:
            missing_settings.append("MAIL_HOST")
        if not self.username:
            missing_settings.append("MAIL_USERNAME")
        if not self.password:
            missing_settings.append("MAIL_PASSWORD")

        if missing_settings:
            raise ValueError(
                "Canlı posta kutusu için eksik ayar var: "
                + ", ".join(missing_settings)
            )

    def _connect(self):
        self._validate_configuration()

        try:
            if self.use_ssl:
                mailbox = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                mailbox = imaplib.IMAP4(self.host, self.port)

            mailbox.login(self.username, self.password)
            return mailbox
        except imaplib.IMAP4.error as error:
            raise ConnectionError(
                "IMAP bağlantısı kurulamadı. Gmail uygulama şifresini ve "
                "hesap bilgilerini kontrol edin."
            ) from error
        except OSError as error:
            raise ConnectionError(
                "IMAP sunucusuna ulaşılamadı. Host, port veya ağ bağlantısını kontrol edin."
            ) from error

    def fetch_messages(self, limit: int) -> list[dict]:
        mailbox = self._connect()

        try:
            select_status, _ = mailbox.select(self.folder)
            if select_status != "OK":
                raise ConnectionError(f"Posta kutusu açılamadı: {self.folder}")

            search_status, search_data = mailbox.search(None, "ALL")
            if search_status != "OK" or not search_data:
                return []

            message_ids = search_data[0].split()
            latest_message_ids = list(reversed(message_ids[-limit:]))
            messages = []

            for message_id in latest_message_ids:
                fetch_status, fetch_data = mailbox.fetch(message_id, "(RFC822)")
                if fetch_status != "OK":
                    continue

                raw_message = next(
                    (
                        item[1]
                        for item in fetch_data
                        if isinstance(item, tuple) and len(item) > 1
                    ),
                    None,
                )
                if not raw_message:
                    continue

                messages.append(
                    normalize_connector_message(
                        self._parse_message(raw_message),
                        self.config.source_mailbox,
                    )
                )

            return messages
        finally:
            try:
                mailbox.close()
            except imaplib.IMAP4.error:
                pass
            mailbox.logout()

    def test_connection(self) -> dict:
        mailbox = self._connect()

        try:
            select_status, select_data = mailbox.select(self.folder)
            if select_status != "OK":
                raise ConnectionError(f"Posta kutusu açılamadı: {self.folder}")

            return {
                "connector_id": self.config.connector_id,
                "status": "ready",
                "message": "Canlı posta kutusu okunabilir durumda.",
                "source_mailbox": self.config.source_mailbox,
                "available_message_count": int(select_data[0] or 0),
            }
        finally:
            try:
                mailbox.close()
            except imaplib.IMAP4.error:
                pass
            mailbox.logout()

    def _parse_message(self, raw_message: bytes) -> dict:
        parsed_message = BytesParser(policy=policy.default).parsebytes(raw_message)

        return {
            "subject": decode_mime_text(parsed_message.get("subject", "")),
            "sender": parse_sender(parsed_message.get("from", "")),
            "body": extract_body_text(parsed_message),
            "source_mailbox": self.config.source_mailbox,
            "has_attachment": bool(extract_attachment_names(parsed_message)),
            "attachment_names": extract_attachment_names(parsed_message),
        }


def decode_mime_text(value: str) -> str:
    if not value:
        return ""

    return str(make_header(decode_header(value))).strip()


def parse_sender(value: str) -> str:
    _, address = parseaddr(decode_mime_text(value))
    return address or decode_mime_text(value)


def extract_attachment_names(message) -> list[str]:
    attachment_names = []

    for part in message.walk():
        filename = part.get_filename()
        if filename:
            attachment_names.append(decode_mime_text(filename))

    return attachment_names


def strip_html(html_text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", html_text)
    return re.sub(r"\s+", " ", without_tags).strip()


def extract_body_text(message) -> str:
    plain_parts = []
    html_parts = []

    for part in message.walk():
        if part.get_content_maintype() == "multipart":
            continue

        disposition = part.get_content_disposition()
        if disposition == "attachment":
            continue

        content_type = part.get_content_type()
        try:
            content = part.get_content()
        except (LookupError, UnicodeDecodeError):
            payload = part.get_payload(decode=True) or b""
            content = payload.decode("utf-8", errors="ignore")

        if content_type == "text/plain":
            plain_parts.append(content.strip())
        elif content_type == "text/html":
            html_parts.append(strip_html(content))

    body = "\n\n".join(part for part in plain_parts if part)

    if not body:
        body = "\n\n".join(part for part in html_parts if part)

    return body.strip()


def normalize_connector_message(message: dict, default_source_mailbox: str) -> dict:
    attachment_names = message.get("attachment_names") or []

    return {
        "subject": message.get("subject", "").strip(),
        "sender": message.get("sender", "").strip(),
        "body": message.get("body", "").strip(),
        "source_mailbox": message.get("source_mailbox") or default_source_mailbox,
        "has_attachment": bool(message.get("has_attachment") or attachment_names),
        "attachment_names": attachment_names,
        "attachment_texts": message.get("attachment_texts", []),
        "expected_category": message.get("expected_category"),
        "expected_department": message.get("expected_department"),
        "expected_priority": message.get("expected_priority"),
        "requires_human_review": message.get("requires_human_review", False),
    }


def build_connector(connector_id: str, source_mailbox: str) -> MailConnector:
    if connector_id == "synthetic_demo":
        return SyntheticMailboxConnector(source_mailbox=source_mailbox)

    if connector_id == "imap":
        return ImapMailboxConnector(
            connector_id="imap",
            name="IMAP / SMTP Connector",
            source_type="IMAP / SMTP",
            source_mailbox=source_mailbox,
        )

    if connector_id == "gmail":
        return ImapMailboxConnector(
            connector_id="gmail",
            name="Gmail IMAP Connector",
            source_type="Gmail",
            source_mailbox=source_mailbox,
            default_host="imap.gmail.com",
        )

    if connector_id == "microsoft365":
        return PlannedMailConnector(
            connector_id="microsoft365",
            name="Microsoft 365 / Exchange Connector",
            source_type="Outlook / Microsoft 365",
            source_mailbox=source_mailbox,
            required_settings=[
                "Tenant id",
                "Client id",
                "Client secret",
                "Graph Mail.Read yetkisi",
                "Ortak posta kutusu adresi",
            ],
            next_step="Graph API yetkileri verildiğinde ortak kutu canlı okunur.",
        )

    raise ValueError(f"Unsupported mail connector: {connector_id}")


def get_mail_connector_overview(source_mailbox: str = "webmaster@rekabet.gov.tr") -> list[dict]:
    connectors = [
        build_connector("synthetic_demo", source_mailbox),
        build_connector("imap", source_mailbox),
        build_connector("gmail", source_mailbox),
        build_connector("microsoft365", source_mailbox),
    ]

    return [
        {
            "connector_id": connector.config.connector_id,
            "name": connector.config.name,
            "source_type": connector.config.source_type,
            "mode": connector.config.mode,
            "status": connector.config.status,
            "source_mailbox": connector.config.source_mailbox,
            "capabilities": connector.config.capabilities,
            "required_settings": connector.config.required_settings,
            "next_step": connector.config.next_step,
        }
        for connector in connectors
    ]
