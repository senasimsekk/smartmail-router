import unittest
from datetime import datetime

from app.services.authorization_service import (
    get_available_roles,
    role_has_permission,
)
from app.services.classification_service import classify_email
from app.services.sla_service import calculate_sla


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


if __name__ == "__main__":
    unittest.main()
