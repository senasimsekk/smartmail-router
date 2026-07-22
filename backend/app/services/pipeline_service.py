PIPELINE_STEP_ORDER = [
    "received",
    "preprocessing",
    "attachments",
    "security",
    "classification",
    "summary",
    "routing",
    "ticket",
    "notification",
]


STATUS_LABELS = {
    "completed": "Tamamlandı",
    "active": "İşlemde",
    "review": "İnceleme gerekli",
    "warning": "Uyarı",
    "waiting": "Bekliyor",
    "skipped": "Atlandı",
}


def has_log(logs: list[dict], action_type: str) -> bool:
    return any(log.get("action_type") == action_type for log in logs or [])


def build_step(
    step_id: str,
    title: str,
    status: str,
    detail: str,
    evidence: list[str] | None = None,
    action: str | None = None,
) -> dict:
    return {
        "id": step_id,
        "order": PIPELINE_STEP_ORDER.index(step_id) + 1,
        "title": title,
        "status": status,
        "status_label": STATUS_LABELS[status],
        "detail": detail,
        "evidence": evidence or [],
        "action": action,
    }


def build_received_step(email: dict, logs: list[dict]) -> dict:
    evidence = [email.get("source_mailbox") or "Kaynak kutu bilinmiyor"]

    if has_log(logs, "EMAIL_IMPORTED"):
        evidence.append("İçe aktarma günlüğü bulundu")

    return build_step(
        step_id="received",
        title="E-posta Alındı",
        status="completed",
        detail="E-posta ortak kutudan sisteme alındı.",
        evidence=evidence,
    )


def build_preprocessing_step(preprocessing: dict) -> dict:
    spam_or_auto = preprocessing.get("spam_or_automatic", {})
    status = "warning" if spam_or_auto.get("is_spam_like") else "completed"
    evidence = [
        f"Dil: {preprocessing.get('language') or 'Bilinmiyor'}",
        f"Ek sayısı: {len(preprocessing.get('attachments', {}).get('all_names', []))}",
    ]

    if preprocessing.get("signature"):
        evidence.append("İmza ayrıştırıldı")

    if preprocessing.get("footer"):
        evidence.append("Footer temizlendi")

    if preprocessing.get("previous_replies"):
        evidence.append("Önceki yazışma zinciri ayrıldı")

    return build_step(
        step_id="preprocessing",
        title="Ön İşleme",
        status=status,
        detail="HTML, imza, footer ve cevap zinciri temizlenerek modele uygun metin üretildi.",
        evidence=evidence,
        action="Spam/otomatik yanıt işaretliyse operatör kontrolü önerilir."
        if status == "warning"
        else None,
    )


def build_attachment_step(email: dict, attachment_analysis: dict) -> dict:
    if not email.get("has_attachment"):
        return build_step(
            step_id="attachments",
            title="Ek Analizi",
            status="skipped",
            detail="E-postada ek dosya bulunmadığı için bu adım atlandı.",
        )

    attachments = attachment_analysis.get("attachments", [])
    risky_count = sum(
        attachment.get("risk_level") in ["Kritik", "Yüksek", "Orta"]
        for attachment in attachments
    )
    status = "warning" if risky_count else "completed"

    return build_step(
        step_id="attachments",
        title="Ek Analizi",
        status=status,
        detail=f"{len(attachments)} ek dosya tür, OCR ihtiyacı ve içerik sinyalleriyle incelendi.",
        evidence=[
            f"Genel risk: {attachment_analysis.get('overall_risk_level', 'Düşük')}",
            f"Kayıt gerektiren ek: {sum(attachment.get('requires_record', False) for attachment in attachments)}",
            f"İnsan onayı isteyen ek: {sum(attachment.get('requires_human_review', False) for attachment in attachments)}",
        ],
        action="Riskli ekler için operatör incelemesi önerilir." if status == "warning" else None,
    )


def build_security_step(email: dict, attachment_analysis: dict) -> dict:
    if not email.get("has_attachment"):
        return build_step(
            step_id="security",
            title="Güvenlik Kontrolü",
            status="skipped",
            detail="Ek olmadığı için dosya güvenlik kontrolü çalışmadı.",
        )

    attachments = attachment_analysis.get("attachments", [])
    warning_count = sum(
        bool(attachment.get("security_warnings"))
        or attachment.get("malware_risk") in ["Şüpheli", "Yüksek"]
        or attachment.get("is_encrypted")
        for attachment in attachments
    )
    status = "warning" if warning_count else "completed"

    return build_step(
        step_id="security",
        title="Güvenlik Kontrolü",
        status=status,
        detail="Ekler şifre, boyut, zararlı dosya riski ve kişisel veri sinyalleri açısından kontrol edildi.",
        evidence=[
            f"Uyarılı ek: {warning_count}",
            f"Kişisel veri içeren ek: {sum(attachment.get('contains_personal_data', False) for attachment in attachments)}",
        ],
        action="Uyarılı ekler açılmadan önce güvenlik kontrolünden geçirilmelidir."
        if status == "warning"
        else None,
    )


def build_classification_step(email: dict, classification: dict) -> dict:
    confidence = classification.get("confidence_score") or 0
    routing_status = email.get("routing_status") or "New"
    status = (
        "completed"
        if routing_status in ["Approved", "Routed", "Corrected", "Completed", "Archived"]
        else "review"
        if classification.get("requires_human_review") or confidence < 0.85
        else "completed"
    )

    return build_step(
        step_id="classification",
        title="Sınıflandırma",
        status=status,
        detail=f"{classification.get('category')} kategorisi ve {classification.get('department')} birimi önerildi.",
        evidence=[
            f"Güven skoru: %{round(confidence * 100)}",
            f"Öncelik: {classification.get('priority')}",
        ],
        action="Güven skoru veya kritik kategori nedeniyle insan onayı beklenir."
        if status == "review"
        else None,
    )


def build_summary_step(analysis: dict) -> dict:
    summary = analysis.get("summary", "")

    return build_step(
        step_id="summary",
        title="Özetleme",
        status="completed" if summary else "waiting",
        detail="Mail gövdesi ve ek metni sinyallerinden karar destek özeti üretildi."
        if summary
        else "Özet henüz üretilemedi.",
        evidence=[summary[:220] + ("..." if len(summary) > 220 else "")]
        if summary
        else [],
    )


def build_routing_step(email: dict, classification: dict, analysis: dict) -> dict:
    routing_status = email.get("routing_status") or "New"
    routing_decision = analysis.get("routing_decision", {})

    if routing_status in ["Routed", "Approved", "Corrected"]:
        status = "completed"
    elif routing_status == "Pending Review" or classification.get("requires_human_review"):
        status = "review"
    else:
        status = "active"

    return build_step(
        step_id="routing",
        title="Yönlendirme Kararı",
        status=status,
        detail=routing_decision.get("routing_type") or "Yönlendirme kararı hazırlanıyor.",
        evidence=[
            f"Hedef birim: {routing_decision.get('primary_department') or classification.get('department')}",
            f"Kayıt durumu: {routing_status}",
        ],
        action=analysis.get("suggested_action") if status in ["review", "active"] else None,
    )


def build_ticket_step(ticket: dict | None, analysis: dict) -> dict:
    operation_type = analysis.get("operation_type", "")

    if ticket:
        return build_step(
            step_id="ticket",
            title="Evrak/Talep Kaydı",
            status="completed",
            detail=f"{ticket.get('record_number')} numaralı kayıt oluşturuldu.",
            evidence=[
                f"Durum: {ticket.get('status_label') or ticket.get('status')}",
                f"Sorumlu birim: {ticket.get('assigned_department')}",
            ],
        )

    if operation_type == "Evrak kaydı gerekiyor":
        return build_step(
            step_id="ticket",
            title="Evrak/Talep Kaydı",
            status="active",
            detail="Bu e-posta için evrak veya talep kaydı açılması öneriliyor.",
            action="Kayıt oluştur butonu ile kayıt açılmalı.",
        )

    return build_step(
        step_id="ticket",
        title="Evrak/Talep Kaydı",
        status="skipped",
        detail="Bu e-posta için zorunlu kayıt ihtiyacı görünmüyor.",
    )


def build_notification_step(email: dict, ticket: dict | None) -> dict:
    routing_status = email.get("routing_status") or "New"
    notification_target = (
        email.get("approved_department")
        or (ticket or {}).get("assigned_department")
        or "İlgili birim"
    )

    if routing_status in ["Routed", "Approved", "Completed", "Archived"]:
        return build_step(
            step_id="notification",
            title="Bildirim",
            status="completed",
            detail="Yönlendirme sonrası ilgili birim bilgilendirme adımına hazır.",
            evidence=[f"Hedef: {notification_target}"],
        )

    return build_step(
        step_id="notification",
        title="Bildirim",
        status="waiting",
        detail="Bildirim için önce yönlendirme veya operatör onayı tamamlanmalı.",
    )


def summarize_pipeline(steps: list[dict]) -> dict:
    completed_statuses = {"completed", "skipped"}
    completed_count = sum(step["status"] in completed_statuses for step in steps)
    attention_count = sum(step["status"] in {"review", "warning", "active"} for step in steps)
    current_step = next(
        (step for step in steps if step["status"] in ["review", "warning", "active", "waiting"]),
        steps[-1],
    )

    return {
        "step_count": len(steps),
        "completed_count": completed_count,
        "attention_count": attention_count,
        "progress_percent": round(completed_count / len(steps), 2) if steps else 0,
        "current_step": current_step,
    }


def build_email_pipeline(
    email: dict,
    classification: dict,
    analysis: dict,
    preprocessing: dict,
    logs: list[dict] | None = None,
    ticket: dict | None = None,
) -> dict:
    attachment_analysis = analysis.get("attachment_analysis", {})
    steps = [
        build_received_step(email, logs or []),
        build_preprocessing_step(preprocessing),
        build_attachment_step(email, attachment_analysis),
        build_security_step(email, attachment_analysis),
        build_classification_step(email, classification),
        build_summary_step(analysis),
        build_routing_step(email, classification, analysis),
        build_ticket_step(ticket, analysis),
        build_notification_step(email, ticket),
    ]

    return {
        "summary": summarize_pipeline(steps),
        "steps": steps,
        "edges": [
            {"source": steps[index]["id"], "target": steps[index + 1]["id"]}
            for index in range(len(steps) - 1)
        ],
    }
