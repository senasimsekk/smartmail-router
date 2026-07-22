import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


PROJECT_DIR = Path(__file__).resolve().parents[3]
SYNTHETIC_EMAILS_FILE = PROJECT_DIR / "data" / "synthetic_emails.json"


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
        return PlannedMailConnector(
            connector_id="imap",
            name="IMAP / SMTP Connector",
            source_type="IMAP / SMTP",
            source_mailbox=source_mailbox,
            required_settings=[
                "IMAP host",
                "IMAP port",
                "Kullanıcı adı",
                "Uygulama şifresi",
                "TLS ayarı",
            ],
            next_step="Gmail veya kurumsal mail için IMAP erişimi açıldığında bu connector aktif edilir.",
        )

    if connector_id == "gmail":
        return PlannedMailConnector(
            connector_id="gmail",
            name="Gmail Connector",
            source_type="Gmail",
            source_mailbox=source_mailbox,
            required_settings=[
                "OAuth client id",
                "OAuth client secret",
                "Refresh token",
                "Okunacak etiket veya posta kutusu",
            ],
            next_step="Demo Gmail hesabı açıldıktan sonra OAuth veya IMAP app password ile bağlanır.",
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
