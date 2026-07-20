from datetime import UTC, datetime, timedelta
from random import Random

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.email import Email
from app.models.system_log import SystemLog
from app.models.ticket import Ticket
from app.services.system_log_service import create_system_log


INTEGRATION_CATALOG = [
    {
        "id": "ad_ldap",
        "name": "Active Directory / LDAP",
        "group": "Kimlik ve Yetki",
        "direction": "İçe Aktarım",
        "owner": "Bilgi İşlem",
        "mode": "Sentetik dizin",
        "endpoint_hint": "ldap://kurum.local",
        "capabilities": [
            "Kullanıcı ve birim eşleştirme",
            "Rol tabanlı yetki aktarımı",
            "Pasif kullanıcı uyarısı",
        ],
        "data_contract": "kullanıcı, birim, unvan, e-posta, grup",
        "next_step": "Gerçek LDAP sunucu bilgileri geldiğinde bağlayıcı aktif edilir.",
    },
    {
        "id": "keycloak_sso",
        "name": "Keycloak / SSO",
        "group": "Kimlik ve Yetki",
        "direction": "Giriş",
        "owner": "Bilgi İşlem",
        "mode": "Simülasyon",
        "endpoint_hint": "https://sso.kurum.local/realms/rekabet",
        "capabilities": [
            "Tek oturum açma",
            "Rol iddiası okuma",
            "Oturum süresi politikası",
        ],
        "data_contract": "kullanıcı kimliği, rol, birim, oturum süresi",
        "next_step": "OIDC istemci bilgileri tanımlanır.",
    },
    {
        "id": "exchange_outlook",
        "name": "Exchange / Outlook",
        "group": "E-posta",
        "direction": "İçe Aktarım",
        "owner": "Evrak Operasyonu",
        "mode": "Sentetik posta kutusu",
        "endpoint_hint": "webmaster@rekabet.gov.tr",
        "capabilities": [
            "Ortak posta kutusu okuma",
            "Birim kutularına yönlendirme",
            "Ek ve gövde birlikte alma",
        ],
        "data_contract": "konu, gönderen, gövde, ekler, posta kutusu",
        "next_step": "Graph API veya IMAP yetkisiyle canlı alma açılır.",
    },
    {
        "id": "ebys",
        "name": "EBYS",
        "group": "Evrak ve Kayıt",
        "direction": "Çift Yönlü",
        "owner": "Evrak Kayıt",
        "mode": "Kayıt simülasyonu",
        "endpoint_hint": "EBYS kayıt servisi",
        "capabilities": [
            "Kayıt numarası alma",
            "Mail ve ekleri kayda bağlama",
            "Durum bilgisini geri okuma",
        ],
        "data_contract": "kayıt no, başvuru türü, birim, ek listesi",
        "next_step": "EBYS REST veya servis sözleşmesi alınır.",
    },
    {
        "id": "kep",
        "name": "KEP Sistemi",
        "group": "Resmi Yazışma",
        "direction": "İçe Aktarım",
        "owner": "Hukuk Müşavirliği",
        "mode": "Doküman çıktısı simülasyonu",
        "endpoint_hint": "kep.rekabet.gov.tr",
        "capabilities": [
            "KEP çıktılarını tanıma",
            "Tebligat tarihi çıkarma",
            "Delil niteliğinde arşivleme",
        ],
        "data_contract": "KEP zarfı, tarih, taraf, belge özeti",
        "next_step": "KEP sağlayıcı entegrasyon dokümanı beklenir.",
    },
    {
        "id": "dms",
        "name": "DMS / Doküman Yönetimi",
        "group": "Doküman",
        "direction": "Dışa Aktarım",
        "owner": "Evrak Kayıt",
        "mode": "Nesne deposu simülasyonu",
        "endpoint_hint": "dms.kurum.local",
        "capabilities": [
            "Ek dosya arşivleme",
            "Metadata ile belge arama",
            "Şifreli dosya uyarısı",
        ],
        "data_contract": "dosya, içerik tipi, özet, kişisel veri bayrağı",
        "next_step": "DMS klasör ve yetki modeli eşleştirilir.",
    },
    {
        "id": "project_management",
        "name": "OpenProject / Jira",
        "group": "İş Takibi",
        "direction": "Dışa Aktarım",
        "owner": "İlgili Birim",
        "mode": "Talep kaydı simülasyonu",
        "endpoint_hint": "proje.kurum.local",
        "capabilities": [
            "Talep kartı açma",
            "SLA tarihini görev son tarihi yapma",
            "Sorumlu kişi atama",
        ],
        "data_contract": "talep başlığı, açıklama, sorumlu, son tarih",
        "next_step": "Kullanılacak iş takip aracı netleştirilir.",
    },
    {
        "id": "collaboration",
        "name": "Teams / Mattermost / Zulip",
        "group": "Bildirim",
        "direction": "Dışa Aktarım",
        "owner": "Operasyon",
        "mode": "Kanal bildirimi simülasyonu",
        "endpoint_hint": "birim kanalı",
        "capabilities": [
            "Kritik mail bildirimi",
            "SLA yaklaşan kayıt uyarısı",
            "Operatör onayı isteme",
        ],
        "data_contract": "başlık, risk, birim, aksiyon bağlantısı",
        "next_step": "Kanal ve webhook adresleri tanımlanır.",
    },
    {
        "id": "notification",
        "name": "SMS / E-posta Bildirim",
        "group": "Bildirim",
        "direction": "Dışa Aktarım",
        "owner": "Operasyon",
        "mode": "Bildirim simülasyonu",
        "endpoint_hint": "sms.kurum.local",
        "capabilities": [
            "Kritik kayıt bildirimi",
            "Kapanış bilgilendirmesi",
            "Başvuru sahibine otomatik cevap",
        ],
        "data_contract": "alıcı, şablon, kayıt no, durum",
        "next_step": "Bildirim şablonları onaylanır.",
    },
    {
        "id": "siem",
        "name": "SIEM / Log Sistemi",
        "group": "Güvenlik",
        "direction": "Dışa Aktarım",
        "owner": "Siber Güvenlik",
        "mode": "Log aktarım simülasyonu",
        "endpoint_hint": "siem.kurum.local",
        "capabilities": [
            "Güvenlik olaylarını aktarma",
            "Operatör işlem izlerini gönderme",
            "Şüpheli ek alarmı üretme",
        ],
        "data_contract": "olay türü, aktör, zaman, risk, kaynak",
        "next_step": "Syslog veya REST log formatı seçilir.",
    },
    {
        "id": "object_storage",
        "name": "MinIO / S3",
        "group": "Altyapı",
        "direction": "Dışa Aktarım",
        "owner": "Bilgi İşlem",
        "mode": "Dosya deposu simülasyonu",
        "endpoint_hint": "s3://smartmail-ekler",
        "capabilities": [
            "Ek dosya saklama",
            "İmzalı indirme bağlantısı",
            "Arşiv yaşam döngüsü",
        ],
        "data_contract": "nesne yolu, dosya özeti, erişim etiketi",
        "next_step": "Bucket, erişim anahtarı ve saklama politikası tanımlanır.",
    },
    {
        "id": "antivirus",
        "name": "Antivirüs Servisi",
        "group": "Güvenlik",
        "direction": "Kontrol",
        "owner": "Siber Güvenlik",
        "mode": "Tarama simülasyonu",
        "endpoint_hint": "clamav.kurum.local",
        "capabilities": [
            "Ek dosya taraması",
            "Şüpheli dosya karantinası",
            "Şifreli arşiv uyarısı",
        ],
        "data_contract": "dosya adı, imza sonucu, risk, uyarı",
        "next_step": "Kurumsal antivirüs REST veya ICAP servisi bağlanır.",
    },
    {
        "id": "webhook_api",
        "name": "Webhook / REST API",
        "group": "Dış Sistem",
        "direction": "Çift Yönlü",
        "owner": "Entegrasyon Ekibi",
        "mode": "Geliştirici arabirimi",
        "endpoint_hint": "/api/events/email-routed",
        "capabilities": [
            "Yönlendirme olayını dışarı bildirme",
            "Dış sistemden mail kaydı alma",
            "Durum güncellemesi kabul etme",
        ],
        "data_contract": "olay türü, kayıt id, hedef birim, durum",
        "next_step": "İmzalı webhook ve IP kısıtı eklenir.",
    },
]


DIRECTORY_UNITS = [
    {
        "unit": "Hukuk Müşavirliği",
        "mailbox": "hukuk@rekabet.gov.tr",
        "synthetic_users": 8,
        "routing_role": "Hukuki tebligat ve KEP çıktıları",
    },
    {
        "unit": "Bilgi İşlem",
        "mailbox": "destek@rekabet.gov.tr",
        "synthetic_users": 6,
        "routing_role": "Teknik destek ve sistem bildirimleri",
    },
    {
        "unit": "Basın ve Halkla İlişkiler",
        "mailbox": "basin@rekabet.gov.tr",
        "synthetic_users": 4,
        "routing_role": "Basın talepleri ve kamuoyu soruları",
    },
    {
        "unit": "Satın Alma",
        "mailbox": "satinalma@rekabet.gov.tr",
        "synthetic_users": 5,
        "routing_role": "Teklif, fatura ve ödeme talepleri",
    },
    {
        "unit": "Evrak Kayıt",
        "mailbox": "evrak@rekabet.gov.tr",
        "synthetic_users": 7,
        "routing_role": "Genel başvuru ve evrak kayıt işlemleri",
    },
]


DATA_FLOWS = [
    {
        "source": "Exchange / Outlook",
        "target": "E-posta Alma",
        "payload": "Mail gövdesi, ekler, kaynak kutu",
        "status": "Simüle edildi",
    },
    {
        "source": "E-posta Alma",
        "target": "EBYS",
        "payload": "Kayıt no, başvuru türü, ek listesi",
        "status": "MVP hazır",
    },
    {
        "source": "Ek Analizi",
        "target": "Antivirüs Servisi",
        "payload": "Dosya adı, imza sonucu, risk seviyesi",
        "status": "Simüle edildi",
    },
    {
        "source": "Yönlendirme",
        "target": "Teams / Mattermost / Zulip",
        "payload": "Kritik kayıt ve SLA uyarısı",
        "status": "Planlandı",
    },
    {
        "source": "İşlem Günlüğü",
        "target": "SIEM / Log Sistemi",
        "payload": "Aktör, işlem, zaman, sonuç",
        "status": "MVP hazır",
    },
    {
        "source": "Ek Depolama",
        "target": "MinIO / S3",
        "payload": "Dosya yolu, erişim etiketi, saklama süresi",
        "status": "Planlandı",
    },
]


SECURITY_CONTROLS = [
    {
        "name": "Kimlik doğrulama",
        "coverage": "Keycloak / SSO ile tek giriş tasarlandı.",
        "status": "Simülasyon",
    },
    {
        "name": "Yetki matrisi",
        "coverage": "Rol bazlı ekran ve işlem yetkileri uygulanıyor.",
        "status": "MVP hazır",
    },
    {
        "name": "Dosya güvenliği",
        "coverage": "Antivirüs, şifreli dosya ve kişisel veri uyarıları simüle ediliyor.",
        "status": "MVP hazır",
    },
    {
        "name": "Denetim izi",
        "coverage": "Kritik işlemler sistem günlüğüne yazılıyor.",
        "status": "MVP hazır",
    },
]


def iso_now() -> str:
    return datetime.now(UTC).isoformat()


def serialize_datetime(value: datetime | None) -> str | None:
    if not value:
        return None

    return value.isoformat()


def get_latest_log_at(logs: list[SystemLog], action_type: str | None = None) -> str | None:
    for log in logs:
        if action_type is None or log.action_type == action_type:
            return serialize_datetime(log.created_at)

    return None


def safe_model_count(db: Session, model) -> int:
    try:
        return db.query(model).count()
    except SQLAlchemyError:
        db.rollback()
        return 0


def build_integration_status(
    integration: dict,
    index: int,
    email_count: int,
    ticket_count: int,
    logs: list[SystemLog],
) -> dict:
    randomizer = Random(f"{integration['id']}-{email_count}-{ticket_count}")
    health_score = max(62, min(99, 86 + randomizer.randint(-10, 8)))
    warning_ids = {"kep", "object_storage", "collaboration"}
    planned_ids = {"project_management", "object_storage"}

    if integration["id"] in planned_ids:
        status = "Planlandı"
        health_score = min(health_score, 72)
    elif integration["id"] in warning_ids:
        status = "Uyarı"
        health_score = min(health_score, 78)
    else:
        status = "Hazır"

    if integration["id"] == "exchange_outlook":
        last_sync_at = get_latest_log_at(logs, "MAILBOX_SYNCED")
    elif integration["id"] == "ebys":
        last_sync_at = get_latest_log_at(logs, "TICKET_CREATED")
    elif integration["id"] == "siem":
        last_sync_at = get_latest_log_at(logs)
    else:
        last_sync_at = serialize_datetime(
            datetime.now(UTC) - timedelta(hours=4 + index * 3)
        )

    return {
        **integration,
        "status": status,
        "health_score": health_score,
        "risk_level": "Düşük" if health_score >= 82 else "Orta",
        "last_sync_at": last_sync_at,
        "records_touched": email_count if integration["group"] == "E-posta" else ticket_count,
        "is_simulated": integration["mode"] != "Geliştirici arabirimi",
    }


def build_integration_overview(db: Session) -> dict:
    email_count = safe_model_count(db, Email)
    ticket_count = safe_model_count(db, Ticket)

    try:
        logs = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(50).all()
    except SQLAlchemyError:
        db.rollback()
        logs = []

    integrations = [
        build_integration_status(
            integration,
            index,
            email_count,
            ticket_count,
            logs,
        )
        for index, integration in enumerate(INTEGRATION_CATALOG)
    ]

    ready_count = sum(1 for integration in integrations if integration["status"] == "Hazır")
    warning_count = sum(1 for integration in integrations if integration["status"] == "Uyarı")
    planned_count = sum(1 for integration in integrations if integration["status"] == "Planlandı")
    simulated_count = sum(1 for integration in integrations if integration["is_simulated"])
    average_health = round(
        sum(integration["health_score"] for integration in integrations) / len(integrations)
    )

    return {
        "generated_at": iso_now(),
        "summary": {
            "total_integrations": len(integrations),
            "ready_count": ready_count,
            "warning_count": warning_count,
            "planned_count": planned_count,
            "simulated_count": simulated_count,
            "average_health": average_health,
            "inbound_count": sum(
                1 for integration in integrations if integration["direction"] in {"İçe Aktarım", "Giriş"}
            ),
            "outbound_count": sum(
                1 for integration in integrations if integration["direction"] == "Dışa Aktarım"
            ),
        },
        "integrations": integrations,
        "directory_units": DIRECTORY_UNITS,
        "data_flows": DATA_FLOWS,
        "security_controls": SECURITY_CONTROLS,
    }


def test_integration_connection(
    db: Session,
    integration_id: str,
    actor_role: str = "operator",
) -> dict:
    overview = build_integration_overview(db)
    integration = next(
        (
            candidate
            for candidate in overview["integrations"]
            if candidate["id"] == integration_id
        ),
        None,
    )

    if not integration:
        raise ValueError("Entegrasyon bulunamadı.")

    is_success = integration["status"] in {"Hazır", "Uyarı"}
    randomizer = Random(f"test-{integration_id}-{integration['health_score']}")
    latency_ms = randomizer.randint(80, 620)

    result = {
        "integration_id": integration_id,
        "name": integration["name"],
        "status": "Başarılı" if is_success else "Planlama bekliyor",
        "latency_ms": latency_ms if is_success else None,
        "checked_at": iso_now(),
        "steps": [
            "Kimlik bilgisi kasası kontrol edildi.",
            "Sentetik uç nokta erişimi doğrulandı.",
            "Veri sözleşmesi alanları kontrol edildi.",
        ],
        "recommendation": integration["next_step"],
    }

    create_system_log(
        db,
        action_type="INTEGRATION_TESTED",
        action_detail=f"{integration['name']} entegrasyon bağlantı testi çalıştırıldı.",
        actor=actor_role,
        status="success" if is_success else "warning",
        extra_data=result,
    )

    return {
        "connection_test": result,
        "integration": integration,
    }
