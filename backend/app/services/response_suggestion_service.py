def get_greeting(sender_name: str | None = None) -> str:
    if sender_name:
        return f"Sayın {sender_name},"

    return "Sayın Başvuru Sahibi,"


def get_closing() -> str:
    return (
        "Saygılarımızla,\n"
        "Rekabet Kurumu"
    )


def create_kvkk_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "Kişisel verilerinizle ilgili başvurunuz alınmıştır. Talebiniz, ilgili mevzuat "
        "ve kurum içi süreçler kapsamında değerlendirilmek üzere ilgili birime "
        "yönlendirilmiştir.\n\n"
        "Başvurunuzun sonucu hakkında tarafınıza ayrıca bilgi verilecektir.\n\n"
        f"{closing}"
    )


def create_technical_support_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "Teknik destek talebiniz alınmıştır. Bildirdiğiniz sorun ilgili teknik birime "
        "iletilmiş olup inceleme süreci başlatılmıştır.\n\n"
        "Gerekli görülmesi halinde tarafınızdan ek bilgi talep edilebilir.\n\n"
        f"{closing}"
    )


def create_press_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "Basın talebiniz alınmıştır. Talebiniz Basın ve Halkla İlişkiler birimi "
        "tarafından değerlendirilecektir.\n\n"
        "Değerlendirme sonucunda tarafınıza dönüş yapılacaktır.\n\n"
        f"{closing}"
    )


def create_purchase_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "Satın alma/teklif sürecine ilişkin iletiniz alınmıştır. Talebiniz ilgili "
        "birime yönlendirilmiş olup değerlendirme süreci başlatılmıştır.\n\n"
        "Gerekli olması halinde tarafınızdan ek belge veya bilgi talep edilebilir.\n\n"
        f"{closing}"
    )


def create_legal_notification_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "İletiniz ve varsa ekleri alınmıştır. Hukuki tebligat veya resmi evrak "
        "niteliği taşıyabilecek başvurunuz, kayıt ve inceleme süreçleri için ilgili "
        "birimlere yönlendirilecektir.\n\n"
        f"{closing}"
    )


def create_complaint_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "Şikayet başvurunuz alınmıştır. İletiniz, ilgili birim tarafından incelenmek "
        "üzere değerlendirme sürecine alınmıştır.\n\n"
        "Başvurunuzla ilgili gerekli görülmesi halinde tarafınızdan ek bilgi veya belge "
        "talep edilebilir.\n\n"
        f"{closing}"
    )


def create_report_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "İhbar niteliğindeki bildiriminiz alınmıştır. Bildiriminiz gizlilik ve ilgili "
        "kurumsal süreçler gözetilerek değerlendirilmek üzere ilgili birime "
        "yönlendirilmiştir.\n\n"
        f"{closing}"
    )


def create_information_request_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "Bilgi talebiniz alınmıştır. Talebiniz ilgili birime yönlendirilmiş olup "
        "kurum içi değerlendirme süreci başlatılmıştır.\n\n"
        "Değerlendirme sonucunda tarafınıza bilgi verilecektir.\n\n"
        f"{closing}"
    )


def create_invoice_payment_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "Fatura/ödeme konulu iletiniz alınmıştır. Talebiniz ilgili mali süreçler "
        "kapsamında değerlendirilmek üzere ilgili birime yönlendirilmiştir.\n\n"
        "Gerekli görülmesi halinde tarafınızdan ek bilgi veya belge talep edilebilir.\n\n"
        f"{closing}"
    )


def create_hr_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "İnsan kaynakları sürecine ilişkin iletiniz alınmıştır. Başvurunuz ilgili "
        "birim tarafından değerlendirilecektir.\n\n"
        "Değerlendirme sonucunda gerekli görülmesi halinde tarafınıza dönüş yapılacaktır.\n\n"
        f"{closing}"
    )


def create_general_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "İletiniz alınmıştır. Talebiniz içeriğine göre ilgili birime yönlendirilmiş "
        "olup değerlendirme sürecine alınmıştır.\n\n"
        "Gerekli görülmesi halinde tarafınıza ayrıca dönüş yapılacaktır.\n\n"
        f"{closing}"
    )


def create_missing_information_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "Başvurunuzun değerlendirilebilmesi için ek bilgi veya belgeye ihtiyaç "
        "duyulmaktadır. Lütfen talebinizle ilgili eksik bilgileri ve varsa destekleyici "
        "belgeleri tarafımıza iletiniz.\n\n"
        f"{closing}"
    )


def create_out_of_scope_response(greeting: str, closing: str) -> str:
    return (
        f"{greeting}\n\n"
        "İletiniz incelenmiştir. Başvurunuzun konusu, ilk değerlendirmeye göre kurumumuzun "
        "görev alanı dışında kalıyor olabilir.\n\n"
        f"{closing}"
    )


def determine_response_template_type(
    classification: dict,
    analysis: dict,
    extracted_information: dict,
) -> str:
    category = classification["category"]

    if analysis.get("operation_type") == "Reddedilebilir/spam olabilir":
        return "out_of_scope"

    if extracted_information.get("requested_action") is None and category in [
        "Genel Başvuru",
        "Bilgi Edinme",
    ]:
        return "missing_information"

    if category == "KVKK Başvurusu":
        return "kvkk"

    if category == "Teknik Destek":
        return "technical_support"

    if category == "Basın Talebi":
        return "press"

    if category == "Satın Alma":
        return "purchase"

    if category == "Hukuki Tebligat":
        return "legal_notification"

    if category == "Şikayet":
        return "complaint"

    if category == "İhbar":
        return "report"

    if category == "Bilgi Edinme":
        return "information_request"

    if category in ["Fatura/Ödeme", "Fatura / Ödeme"]:
        return "invoice_payment"

    if category == "İnsan Kaynakları":
        return "hr"

    return "general"


def build_response_by_template(template_type: str, greeting: str, closing: str) -> str:
    if template_type == "kvkk":
        return create_kvkk_response(greeting, closing)

    if template_type == "technical_support":
        return create_technical_support_response(greeting, closing)

    if template_type == "press":
        return create_press_response(greeting, closing)

    if template_type == "purchase":
        return create_purchase_response(greeting, closing)

    if template_type == "legal_notification":
        return create_legal_notification_response(greeting, closing)

    if template_type == "complaint":
        return create_complaint_response(greeting, closing)

    if template_type == "report":
        return create_report_response(greeting, closing)

    if template_type == "information_request":
        return create_information_request_response(greeting, closing)

    if template_type == "invoice_payment":
        return create_invoice_payment_response(greeting, closing)

    if template_type == "hr":
        return create_hr_response(greeting, closing)

    if template_type == "missing_information":
        return create_missing_information_response(greeting, closing)

    if template_type == "out_of_scope":
        return create_out_of_scope_response(greeting, closing)

    return create_general_response(greeting, closing)


def create_response_warning(classification: dict, analysis: dict) -> str:
    if classification.get("requires_human_review"):
        return "Bu mail insan onayı gerektirdiği için cevap taslağı otomatik gönderilmemelidir."

    if analysis.get("risk_level") in ["Kritik", "Yüksek"]:
        return "Mail yüksek/kritik risk içerdiği için cevap taslağı yetkili personel tarafından kontrol edilmelidir."

    return "Cevap taslağı gönderilmeden önce personel tarafından gözden geçirilmelidir."


def suggest_email_response(
    email: dict,
    classification: dict,
    analysis: dict,
    extracted_information: dict,
) -> dict:
    sender_name = extracted_information.get("sender")
    greeting = get_greeting(sender_name)
    closing = get_closing()

    template_type = determine_response_template_type(
        classification=classification,
        analysis=analysis,
        extracted_information=extracted_information,
    )

    suggested_response = build_response_by_template(
        template_type=template_type,
        greeting=greeting,
        closing=closing,
    )

    needs_human_approval = (
        classification.get("requires_human_review", False)
        or analysis.get("risk_level") in ["Kritik", "Yüksek"]
        or analysis.get("operation_type") in ["Onay gerekiyor", "Evrak kaydı gerekiyor"]
    )

    return {
        "template_type": template_type,
        "auto_send_allowed": False,
        "needs_human_approval": needs_human_approval,
        "warning": create_response_warning(classification, analysis),
        "suggested_response": suggested_response,
    }