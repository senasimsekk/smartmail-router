from collections import Counter
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.services.classification_service import classify_email
from app.services.evaluation_service import evaluate_classification


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def calculate_rate(part: int, total: int) -> float:
    if total == 0:
        return 0

    return round(part / total, 2)


def has_expected_labels(email: dict) -> bool:
    return all(
        [
            email.get("expected_category"),
            email.get("expected_department"),
            email.get("expected_priority"),
        ]
    )


def get_confidence_bucket(confidence_score: float) -> str:
    if confidence_score >= 0.85:
        return "Yüksek güven"

    if confidence_score >= 0.60:
        return "Orta güven"

    return "Düşük güven"


def format_counter_rows(counter: Counter, key_name: str, limit: int = 8) -> list[dict]:
    return [
        {
            key_name: key,
            "count": count,
        }
        for key, count in counter.most_common(limit)
    ]


def build_category_performance(per_category: dict) -> list[dict]:
    rows = []

    for category, values in per_category.items():
        total = values["total"]
        correct = values["correct"]
        rows.append(
            {
                "category": category,
                "total": total,
                "correct": correct,
                "wrong": total - correct,
                "accuracy_rate": calculate_rate(correct, total),
            }
        )

    return sorted(
        rows,
        key=lambda row: (row["accuracy_rate"], -row["total"], row["category"]),
    )


def build_feedback_corrections(feedbacks: list[dict]) -> dict:
    department_corrections = Counter()
    category_corrections = Counter()
    priority_corrections = Counter()
    misdirected_count = 0

    for feedback in feedbacks:
        if feedback.get("is_misdirected"):
            misdirected_count += 1

        if feedback.get("original_department") != feedback.get("corrected_department"):
            department_corrections[
                f"{feedback.get('original_department')} -> {feedback.get('corrected_department')}"
            ] += 1

        if feedback.get("original_category") != feedback.get("corrected_category"):
            category_corrections[
                f"{feedback.get('original_category')} -> {feedback.get('corrected_category')}"
            ] += 1

        if feedback.get("original_priority") != feedback.get("corrected_priority"):
            priority_corrections[
                f"{feedback.get('original_priority')} -> {feedback.get('corrected_priority')}"
            ] += 1

    return {
        "misdirected_count": misdirected_count,
        "department_corrections": format_counter_rows(
            department_corrections,
            "correction",
        ),
        "category_corrections": format_counter_rows(
            category_corrections,
            "correction",
        ),
        "priority_corrections": format_counter_rows(
            priority_corrections,
            "correction",
        ),
    }


def build_recommendations(
    exact_match_rate: float,
    category_accuracy_rate: float,
    feedback_count: int,
    low_confidence_count: int,
    confusion_count: int,
) -> list[str]:
    recommendations = []

    if exact_match_rate < 0.80:
        recommendations.append(
            "Tam eşleşme oranı düşükse eğitim verisi ve kategori kuralları birlikte gözden geçirilmeli."
        )

    if category_accuracy_rate < 0.85:
        recommendations.append(
            "Kategori doğruluğunu artırmak için sık karışan kategorilere örnek mail eklenmeli."
        )

    if feedback_count > 0:
        recommendations.append(
            "Operatör düzeltmeleri eğitim verisine katılarak TF-IDF modeli yeniden eğitilmeli."
        )

    if low_confidence_count > 0:
        recommendations.append(
            "Düşük güvenli kayıtlar otomatik yönlendirilmeden önce insan onayına düşürülmeli."
        )

    if confusion_count > 0:
        recommendations.append(
            "Karışma matrisi en çok hatalı eşleşen kategori çiftlerini önceliklendirmek için kullanılmalı."
        )

    if not recommendations:
        recommendations.append(
            "Mevcut etiketli veri setinde kritik bir iyileştirme alanı görünmüyor; yeni gerçekçi senaryolarla test seti büyütülebilir."
        )

    return recommendations


def build_evaluation_report(emails: list[dict], feedbacks: list[dict] | None = None) -> dict:
    feedbacks = feedbacks or []

    total_emails = len(emails)
    labeled_count = 0
    category_correct_count = 0
    department_correct_count = 0
    priority_correct_count = 0
    human_review_correct_count = 0
    exact_match_count = 0
    low_confidence_count = 0

    confidence_counter = Counter()
    confusion_counter = Counter()
    per_category = {}
    evaluated_rows = []
    sample_errors = []

    for email in emails:
        classification = classify_email(email)
        confidence_score = classification.get("confidence_score") or 0
        confidence_counter[get_confidence_bucket(confidence_score)] += 1

        if confidence_score < 0.60:
            low_confidence_count += 1

        if not has_expected_labels(email):
            continue

        labeled_count += 1
        evaluation = evaluate_classification(email, classification)
        expected = evaluation["expected_result"]
        checks = evaluation["evaluation"]
        exact_match = (
            checks["category_correct"]
            and checks["department_correct"]
            and checks["priority_correct"]
        )

        category_correct_count += int(checks["category_correct"])
        department_correct_count += int(checks["department_correct"])
        priority_correct_count += int(checks["priority_correct"])
        human_review_correct_count += int(checks["requires_human_review_correct"])
        exact_match_count += int(exact_match)

        category_values = per_category.setdefault(
            expected["category"],
            {
                "total": 0,
                "correct": 0,
            },
        )
        category_values["total"] += 1
        category_values["correct"] += int(checks["category_correct"])

        if not checks["category_correct"]:
            confusion_counter[
                f"{expected['category']} -> {classification['category']}"
            ] += 1

        row = {
            "email_id": email.get("id"),
            "subject": email.get("subject"),
            "expected_category": expected["category"],
            "predicted_category": classification["category"],
            "expected_department": expected["department"],
            "predicted_department": classification["department"],
            "expected_priority": expected["priority"],
            "predicted_priority": classification["priority"],
            "confidence_score": confidence_score,
            "exact_match": exact_match,
        }
        evaluated_rows.append(row)

        if not exact_match and len(sample_errors) < 8:
            sample_errors.append(row)

    feedback_corrections = build_feedback_corrections(feedbacks)
    exact_match_rate = calculate_rate(exact_match_count, labeled_count)
    category_accuracy_rate = calculate_rate(category_correct_count, labeled_count)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_emails": total_emails,
            "labeled_email_count": labeled_count,
            "unlabeled_email_count": total_emails - labeled_count,
            "feedback_count": len(feedbacks),
            "misdirected_feedback_count": feedback_corrections["misdirected_count"],
            "low_confidence_count": low_confidence_count,
            "exact_match_count": exact_match_count,
            "wrong_match_count": labeled_count - exact_match_count,
            "exact_match_rate": exact_match_rate,
            "category_accuracy_rate": category_accuracy_rate,
            "department_accuracy_rate": calculate_rate(
                department_correct_count,
                labeled_count,
            ),
            "priority_accuracy_rate": calculate_rate(
                priority_correct_count,
                labeled_count,
            ),
            "human_review_accuracy_rate": calculate_rate(
                human_review_correct_count,
                labeled_count,
            ),
            "feedback_misdirection_rate": calculate_rate(
                feedback_corrections["misdirected_count"],
                len(feedbacks),
            ),
        },
        "confidence_distribution": dict(confidence_counter),
        "category_performance": build_category_performance(per_category),
        "confusion_pairs": format_counter_rows(confusion_counter, "pair"),
        "feedback_corrections": feedback_corrections,
        "sample_errors": sample_errors,
        "evaluated_rows": evaluated_rows[:20],
        "recommendations": build_recommendations(
            exact_match_rate=exact_match_rate,
            category_accuracy_rate=category_accuracy_rate,
            feedback_count=len(feedbacks),
            low_confidence_count=low_confidence_count,
            confusion_count=sum(confusion_counter.values()),
        ),
    }


def get_evaluation_report(db: "Session") -> dict:
    from app.models.email import Email
    from app.models.feedback import Feedback
    from app.services.email_db_service import email_to_dict
    from app.services.feedback_service import feedback_to_dict

    email_records = db.query(Email).order_by(Email.id).all()
    feedback_records = db.query(Feedback).order_by(Feedback.created_at.desc()).all()
    emails = [email_to_dict(email) for email in email_records]
    feedbacks = [feedback_to_dict(feedback) for feedback in feedback_records]

    return build_evaluation_report(emails, feedbacks)
