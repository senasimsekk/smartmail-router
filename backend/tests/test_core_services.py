import unittest
from datetime import datetime

from app.services.authorization_service import (
    get_available_roles,
    role_has_permission,
)
from app.services.attachment_analysis_service import (
    detect_file_security_status,
    detect_personal_data_indicators,
    extract_attachment_entities,
)
from app.services.classification_service import classify_email
from app.services.email_ingestion_service import normalize_attachment_names
from app.services.email_processing_service import determine_processing_routing_decision
from app.services.sla_service import calculate_sla
from app.services.ticket_service import build_record_number, derive_ticket_status


def make_email(**overrides):
    email = {
        "id": 1,
        "subject": "Test mail",
        "sender": "vatandas@example.com",
        "body": "Genel başvuru içeriği.",
        "source_mailbox": "webmaster@rekabet.gov.tr",
        "has_attachment": False,
        "attachment_names": [],
        "attachment_texts": [],
        "routing_status": "New",
        "created_at": "2026-07-15T09:00:00",
    }
    email.update(overrides)
    return email


class ClassificationServiceTests(unittest.TestCase):
    def test_classifies_kvkk_request(self):
        email = make_email(
            subject="Kişisel verilerimin silinmesi talebi",
            body=(
                "KVKK kapsamında kişisel verilerimin silinmesini ve "
                "veri sorumlusu tarafından bilgi verilmesini talep ediyorum."
            ),
        )

        result = classify_email(email)

        self.assertEqual(result["category"], "KVKK Başvurusu")
        self.assertEqual(result["department"], "Hukuk Müşavirliği")
        self.assertEqual(result["priority"], "Yüksek")
        self.assertTrue(result["requires_human_review"])

    def test_contextual_override_sets_website_issue_to_low_priority(self):
        email = make_email(
            subject="Web sitesi bağlantı hatası",
            body="Web sitesi iletişim sayfası çalışmıyor, bağlantı hata veriyor.",
        )

        result = classify_email(email)

        self.assertEqual(result["category"], "Teknik Destek")
        self.assertEqual(result["department"], "Bilgi İşlem")
        self.assertEqual(result["priority"], "Düşük")


class SlaServiceTests(unittest.TestCase):
    def test_marks_legal_notice_as_overdue(self):
        email = make_email(created_at="2026-07-10T10:00:00")
        classification = {"category": "Hukuki Tebligat"}

        sla = calculate_sla(
            email=email,
            classification=classification,
            now=datetime(2026, 7, 16, 12, 0, 0),
        )

        self.assertEqual(sla["status"], "Overdue")
        self.assertEqual(sla["status_label"], "Gecikti")
        self.assertEqual(sla["remaining_days"], -5)

    def test_marks_due_soon_when_one_day_left(self):
        email = make_email(created_at="2026-07-15T10:00:00")
        classification = {"category": "Teknik Destek"}

        sla = calculate_sla(
            email=email,
            classification=classification,
            now=datetime(2026, 7, 16, 12, 0, 0),
        )

        self.assertEqual(sla["status"], "Due soon")
        self.assertEqual(sla["status_label"], "Yaklaşıyor")
        self.assertEqual(sla["remaining_days"], 1)

    def test_closed_routing_status_overrides_remaining_time(self):
        email = make_email(
            created_at="2026-07-10T10:00:00",
            routing_status="Routed",
        )
        classification = {"category": "Hukuki Tebligat"}

        sla = calculate_sla(
            email=email,
            classification=classification,
            now=datetime(2026, 7, 16, 12, 0, 0),
        )

        self.assertEqual(sla["status"], "Closed")
        self.assertEqual(sla["status_label"], "Kapandı")


class AuthorizationServiceTests(unittest.TestCase):
    def test_operator_can_correct_routing(self):
        self.assertTrue(role_has_permission("operator", "correct_routing"))

    def test_viewer_cannot_route_email(self):
        self.assertFalse(role_has_permission("viewer", "route_email"))

    def test_unknown_role_has_no_permissions(self):
        self.assertFalse(role_has_permission("unknown", "view_dashboard"))

    def test_available_roles_include_admin_and_viewer(self):
        roles = {role["role"] for role in get_available_roles()}

        self.assertIn("admin", roles)
        self.assertIn("viewer", roles)


class EmailProcessingServiceTests(unittest.TestCase):
    def test_auto_routes_high_confidence_non_critical_email(self):
        decision = determine_processing_routing_decision(
            {
                "confidence_score": 0.92,
                "requires_human_review": False,
            }
        )

        self.assertEqual(decision["routing_status"], "Routed")
        self.assertTrue(decision["auto_route"])

    def test_sends_critical_email_to_human_review(self):
        decision = determine_processing_routing_decision(
            {
                "confidence_score": 0.95,
                "requires_human_review": True,
            }
        )

        self.assertEqual(decision["routing_status"], "Pending Review")
        self.assertFalse(decision["auto_route"])

    def test_sends_low_confidence_email_to_human_review(self):
        decision = determine_processing_routing_decision(
            {
                "confidence_score": 0.62,
                "requires_human_review": False,
            }
        )

        self.assertEqual(decision["routing_status"], "Pending Review")
        self.assertFalse(decision["auto_route"])


class EmailIngestionServiceTests(unittest.TestCase):
    def test_normalizes_attachment_names(self):
        attachment_names = normalize_attachment_names(
            [" tebligat.pdf ", "", "   ", "kimlik.png"]
        )

        self.assertEqual(attachment_names, ["tebligat.pdf", "kimlik.png"])

    def test_normalizes_empty_attachment_names(self):
        self.assertEqual(normalize_attachment_names(None), [])


class AttachmentAnalysisServiceTests(unittest.TestCase):
    def test_detects_archive_security_warning(self):
        result = detect_file_security_status("belgeler_sifreli.zip")

        self.assertEqual(result["malware_risk"], "Şüpheli")
        self.assertTrue(result["is_encrypted"])

    def test_detects_personal_data_indicators(self):
        result = detect_personal_data_indicators(
            "Başvuru ekinde T.C. kimlik no, telefon ve IBAN bilgisi yer alıyor."
        )

        self.assertTrue(result["contains_personal_data"])
        self.assertIn("T.C. kimlik/vergi no", result["indicators"])
        self.assertIn("Finansal bilgi", result["indicators"])

    def test_extracts_attachment_topic_and_file_number(self):
        result = extract_attachment_entities(
            "uyap_tebligat_2025-1-002.pdf",
            "Mahkeme tebligatı 12/07/2026 tarihinde iletilmiştir.",
        )

        self.assertEqual(result["topic"], "Hukuki evrak")
        self.assertIn("2025-1-002", result["file_numbers"])
        self.assertIn("12/07/2026", result["dates"])


class TicketServiceTests(unittest.TestCase):
    def test_builds_record_number_from_email_id_and_year(self):
        record_number = build_record_number(
            email_id=42,
            created_at=datetime(2026, 7, 17, 12, 0, 0),
        )

        self.assertEqual(record_number, "RK-2026-000042")

    def test_derives_ticket_status_for_routed_email(self):
        status = derive_ticket_status(
            {"routing_status": "Routed"},
            {"requires_human_review": False},
        )

        self.assertEqual(status, "Birimine yönlendirildi")

    def test_derives_ticket_status_for_review_email(self):
        status = derive_ticket_status(
            {"routing_status": "Pending Review"},
            {"requires_human_review": True},
        )

        self.assertEqual(status, "Onay bekliyor")


if __name__ == "__main__":
    unittest.main()
