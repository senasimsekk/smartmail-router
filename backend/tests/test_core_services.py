import unittest
from datetime import datetime
from unittest.mock import patch
from types import SimpleNamespace

from app.services.ai_service import analyze_email_with_mock_ai
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
from app.services.dashboard_service import build_operational_report, calculate_rate
from app.services.email_ingestion_service import normalize_attachment_names
from app.services.email_analysis_service import generate_summary
from app.services.email_processing_service import determine_processing_routing_decision
from app.services.evaluation_report_service import build_evaluation_report
from app.services.integration_service import (
    INTEGRATION_CATALOG,
    build_integration_status,
)
from app.services.preprocessing_service import preprocess_email
from app.services.sla_service import calculate_sla
from app.services.ticket_service import build_record_number, derive_ticket_status
from app.services.trainable_model_service import (
    extract_tfidf_evidence,
    import_ml_dependencies,
    train_single_target_model,
)


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


class TrainableModelServiceTests(unittest.TestCase):
    def test_extracts_tfidf_evidence_terms_for_prediction(self):
        dependencies = import_ml_dependencies()
        model = train_single_target_model(
            [
                "kvkk kisisel veri silinmesi talebi",
                "veri sorumlusu kisisel veri basvurusu",
                "portal sifre giris hatasi",
                "web sitesi baglanti sorunu",
            ],
            [
                "KVKK Başvurusu",
                "KVKK Başvurusu",
                "Teknik Destek",
                "Teknik Destek",
            ],
            dependencies,
        )

        evidence_terms = extract_tfidf_evidence(
            model,
            "kisisel verilerimin silinmesi icin kvkk basvurusu",
        )

        terms = {item["term"] for item in evidence_terms}

        self.assertTrue(evidence_terms)
        self.assertTrue({"kvkk", "kisisel"} & terms)


class EmailAnalysisServiceTests(unittest.TestCase):
    def test_generates_contextual_summary_with_entities_and_attachments(self):
        email = make_email(
            subject="KVKK başvuru sonucu talebi",
            body=(
                "6698 sayılı Kanun kapsamında kişisel verilerimin silinmesini talep ediyorum. "
                "Başvuru numarası: RK-2026-184. Tarih: 16/07/2026. "
                "Dilekçe ekte sunulmuştur."
            ),
            has_attachment=True,
            attachment_names=["kvkk-dilekce.pdf"],
        )
        classification = {
            "category": "KVKK Başvurusu",
            "department": "Hukuk Müşavirliği",
            "priority": "Yüksek",
            "requires_human_review": True,
            "confidence_score": 0.91,
        }

        summary = generate_summary(email, classification)

        self.assertIn("Kişisel verilerin silinmesi talebi", summary)
        self.assertIn("başvuru numarası", summary)
        self.assertIn("16/07/2026", summary)
        self.assertIn("kvkk-dilekce.pdf", summary)
        self.assertIn("Hukuk Müşavirliği", summary)


class AiServiceTests(unittest.TestCase):
    def test_uses_demo_llm_fallback_without_openai_key(self):
        email = make_email(
            subject="Portal giriş hatası",
            body="Portal girişinde şifre hatası alıyorum.",
        )
        classification = {
            "category": "Teknik Destek",
            "department": "Bilgi İşlem",
            "priority": "Normal",
            "requires_human_review": False,
            "confidence_score": 0.91,
            "matched_keywords": ["portal", "şifre"],
        }

        with patch.dict("os.environ", {}, clear=True):
            result = analyze_email_with_mock_ai(email, classification)

        self.assertEqual(result["ai_mode"], "demo")
        self.assertEqual(result["llm_connection"]["status"], "demo_fallback")
        self.assertEqual(
            result["llm_classification"]["ai_department"],
            "Bilgi İşlem",
        )


class EvaluationReportServiceTests(unittest.TestCase):
    def test_builds_evaluation_metrics_from_expected_labels_and_feedback(self):
        emails = [
            make_email(
                id=1,
                subject="KVKK başvurusu",
                body="KVKK kapsamında kişisel verilerimin silinmesini talep ediyorum.",
                expected_category="KVKK Başvurusu",
                expected_department="Hukuk Müşavirliği",
                expected_priority="Yüksek",
                requires_human_review=True,
            ),
            make_email(
                id=2,
                subject="Portal giriş hatası",
                body="Portal girişinde şifre hatası alıyorum.",
                expected_category="Teknik Destek",
                expected_department="Bilgi İşlem",
                expected_priority="Normal",
                requires_human_review=False,
            ),
        ]
        feedbacks = [
            {
                "original_category": "Genel Başvuru",
                "original_department": "Evrak Kayıt",
                "original_priority": "Normal",
                "corrected_category": "Teknik Destek",
                "corrected_department": "Bilgi İşlem",
                "corrected_priority": "Normal",
                "is_misdirected": True,
            }
        ]

        report = build_evaluation_report(emails, feedbacks)

        self.assertEqual(report["summary"]["labeled_email_count"], 2)
        self.assertEqual(report["summary"]["exact_match_rate"], 1)
        self.assertEqual(report["summary"]["feedback_count"], 1)
        self.assertEqual(report["summary"]["misdirected_feedback_count"], 1)
        self.assertEqual(report["category_performance"][0]["accuracy_rate"], 1)


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


class DashboardReportServiceTests(unittest.TestCase):
    def test_calculates_rate_safely(self):
        self.assertEqual(calculate_rate(2, 4), 0.5)
        self.assertEqual(calculate_rate(2, 0), 0)

    def test_builds_management_report_metrics(self):
        emails = [
            make_email(
                id=1,
                subject="KVKK başvurusu",
                body="Kişisel verilerimin silinmesini talep ediyorum.",
                routing_status="Pending Review",
                expected_category="KVKK Başvurusu",
                expected_department="Hukuk Müşavirliği",
                expected_priority="Yüksek",
            ),
            make_email(
                id=2,
                subject="Portal giriş hatası",
                body="Portal girişinde teknik hata alıyorum.",
                routing_status="Routed",
                approved_by="system",
                approved_at="2026-07-15T09:00:42",
                expected_category="Teknik Destek",
                expected_department="Bilgi İşlem",
                expected_priority="Düşük",
            ),
            make_email(
                id=3,
                subject="Otomatik cevap",
                body="Bu otomatik cevap mesajıdır.",
                routing_status="Corrected",
            ),
        ]
        logs = [
            {
                "email_id": 3,
                "action_type": "ROUTING_CORRECTED",
                "actor": "operator",
                "created_at": "2026-07-15T09:01:00",
                "extra_data": {},
            }
        ]

        report = build_operational_report(emails, logs)

        self.assertEqual(report["kpis"]["total_emails"], 3)
        self.assertEqual(report["kpis"]["auto_routed_count"], 1)
        self.assertEqual(report["kpis"]["pending_review_count"], 1)
        self.assertEqual(report["kpis"]["wrong_routing_count"], 1)
        self.assertEqual(report["kpis"]["operator_intervention_rate"], 0.33)
        self.assertGreaterEqual(report["kpis"]["spam_or_automatic_count"], 1)
        self.assertEqual(report["mailbox_performance"][0]["total"], 3)


class IntegrationServiceTests(unittest.TestCase):
    def test_builds_exchange_integration_status_from_latest_mailbox_log(self):
        log = SimpleNamespace(
            action_type="MAILBOX_SYNCED",
            created_at=datetime(2026, 7, 16, 14, 30, 0),
        )
        exchange = next(
            integration
            for integration in INTEGRATION_CATALOG
            if integration["id"] == "exchange_outlook"
        )

        status = build_integration_status(exchange, 2, 20, 4, [log])

        self.assertEqual(status["name"], "Exchange / Outlook")
        self.assertEqual(status["status"], "Hazır")
        self.assertEqual(status["records_touched"], 20)
        self.assertEqual(status["last_sync_at"], "2026-07-16T14:30:00")
        self.assertIn("Ortak posta kutusu okuma", status["capabilities"])

    def test_marks_object_storage_as_planned(self):
        object_storage = next(
            integration
            for integration in INTEGRATION_CATALOG
            if integration["id"] == "object_storage"
        )

        status = build_integration_status(object_storage, 9, 20, 4, [])

        self.assertEqual(status["status"], "Planlandı")
        self.assertLessEqual(status["health_score"], 72)


class EmailIngestionServiceTests(unittest.TestCase):
    def test_normalizes_attachment_names(self):
        attachment_names = normalize_attachment_names(
            [" tebligat.pdf ", "", "   ", "kimlik.png"]
        )

        self.assertEqual(attachment_names, ["tebligat.pdf", "kimlik.png"])

    def test_normalizes_empty_attachment_names(self):
        self.assertEqual(normalize_attachment_names(None), [])


class PreprocessingServiceTests(unittest.TestCase):
    def test_splits_main_message_signature_footer_and_reply_chain(self):
        email = make_email(
            subject="Re: Başvuru",
            sender="ahmet.yilmaz@example.com",
            body=(
                "<p>Merhaba,</p><p>Ekte basvuru.pdf yer almaktadır.</p>"
                "<br>İyi çalışmalar,<br>Ahmet Yılmaz<br>"
                "Bu e-posta ve ekleri gizlidir.<br>"
                "Kimden: onceki@example.com<br>Konu: Eski cevap<br>Eski mesaj"
            ),
            attachment_names=["kimlik.png"],
        )

        result = preprocess_email(email)

        self.assertIn("Ekte basvuru.pdf", result["main_message"])
        self.assertIn("Ahmet Yılmaz", result["signature"])
        self.assertIn("Bu e-posta", result["footer"])
        self.assertEqual(result["language"], "Türkçe")
        self.assertIn("basvuru.pdf", result["attachments"]["detected_in_body"])
        self.assertIn("kimlik.png", result["attachments"]["all_names"])
        self.assertGreaterEqual(len(result["previous_replies"]), 1)

    def test_detects_automatic_reply_and_fixes_broken_characters(self):
        email = make_email(
            subject="Otomatik cevap",
            sender="no-reply@example.com",
            body="Merhaba, Ä°lgili kiÅŸi ofis dışında.",
        )

        result = preprocess_email(email)

        self.assertIn("İlgili kişi", result["plain_text"])
        self.assertTrue(result["spam_or_automatic"]["is_automatic_reply"])


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
