from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.email import Email
from app.models.feedback import Feedback
from app.services.email_db_service import email_to_dict
from app.services.preprocessing_service import build_classification_text


BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BACKEND_DIR / "model_artifacts"
MODEL_PATH = MODEL_DIR / "email_classifier.joblib"
TARGET_FIELDS = ["category", "department", "priority"]
TOP_EVIDENCE_TERM_COUNT = 5


class ModelDependencyError(RuntimeError):
    pass


class ModelNotTrainedError(RuntimeError):
    pass


def import_ml_dependencies():
    try:
        import joblib
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
    except ModuleNotFoundError as error:
        raise ModelDependencyError(
            "Trainable model dependencies are missing. Install backend requirements first."
        ) from error

    return {
        "joblib": joblib,
        "TfidfVectorizer": TfidfVectorizer,
        "LogisticRegression": LogisticRegression,
        "Pipeline": Pipeline,
    }


def build_training_dataset(db: Session) -> list[dict]:
    emails = db.query(Email).order_by(Email.id).all()
    feedbacks = db.query(Feedback).order_by(Feedback.created_at.asc()).all()

    examples = []

    for email_record in emails:
        email = email_to_dict(email_record)

        if not all(
            [
                email.get("expected_category"),
                email.get("expected_department"),
                email.get("expected_priority"),
            ]
        ):
            continue

        examples.append(
            {
                "email_id": email["id"],
                "source": "seed",
                "text": build_classification_text(email),
                "category": email["expected_category"],
                "department": email["expected_department"],
                "priority": email["expected_priority"],
            }
        )

    email_by_id = {email.id: email for email in emails}

    for feedback in feedbacks:
        email_record = email_by_id.get(feedback.email_id)

        if email_record is None:
            continue

        email = email_to_dict(email_record)
        examples.append(
            {
                "email_id": email["id"],
                "source": "feedback",
                "text": build_classification_text(email),
                "category": feedback.corrected_category,
                "department": feedback.corrected_department,
                "priority": feedback.corrected_priority,
            }
        )

    return examples


def train_single_target_model(texts: list[str], labels: list[str], dependencies: dict):
    pipeline = dependencies["Pipeline"](
        [
            (
                "tfidf",
                dependencies["TfidfVectorizer"](
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                ),
            ),
            (
                "classifier",
                dependencies["LogisticRegression"](
                    max_iter=1000,
                    class_weight="balanced",
                    solver="liblinear",
                ),
            ),
        ]
    )

    pipeline.fit(texts, labels)
    return pipeline


def extract_tfidf_evidence(model, text: str, top_count: int = TOP_EVIDENCE_TERM_COUNT) -> list[dict]:
    vectorizer = model.named_steps["tfidf"]
    classifier = model.named_steps["classifier"]
    matrix = vectorizer.transform([text])
    predicted_label = str(model.predict([text])[0])
    feature_names = vectorizer.get_feature_names_out()

    if matrix.nnz == 0:
        return []

    class_labels = [str(label) for label in classifier.classes_]
    predicted_index = class_labels.index(predicted_label)

    if len(class_labels) == 2 and classifier.coef_.shape[0] == 1:
        coefficients = classifier.coef_[0]

        if predicted_index == 0:
            coefficients = -coefficients
    else:
        coefficients = classifier.coef_[predicted_index]

    _, feature_indices = matrix.nonzero()
    weighted_terms = []

    for feature_index in feature_indices:
        tfidf_weight = float(matrix[0, feature_index])
        contribution = tfidf_weight * float(coefficients[feature_index])

        if contribution <= 0:
            continue

        weighted_terms.append(
            {
                "term": feature_names[feature_index],
                "weight": round(tfidf_weight, 3),
                "contribution": round(contribution, 3),
            }
        )

    weighted_terms.sort(key=lambda item: item["contribution"], reverse=True)
    return weighted_terms[:top_count]


def train_email_classifier(db: Session) -> dict:
    dependencies = import_ml_dependencies()
    examples = build_training_dataset(db)

    if len(examples) < 4:
        raise ValueError("At least 4 labeled training examples are required.")

    texts = [example["text"] for example in examples]
    models = {}
    label_distribution = {}

    for target in TARGET_FIELDS:
        labels = [example[target] for example in examples]
        distribution = Counter(labels)

        if len(distribution) < 2:
            raise ValueError(
                f"Target '{target}' needs at least 2 different labels to train."
            )

        models[target] = train_single_target_model(texts, labels, dependencies)
        label_distribution[target] = dict(distribution)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    artifact = {
        "models": models,
        "metadata": {
            "trained_at": datetime.utcnow().isoformat(),
            "training_example_count": len(examples),
            "feedback_example_count": sum(
                1 for example in examples if example["source"] == "feedback"
            ),
            "seed_example_count": sum(
                1 for example in examples if example["source"] == "seed"
            ),
            "label_distribution": label_distribution,
            "model_type": "TF-IDF + Logistic Regression",
        },
    }

    dependencies["joblib"].dump(artifact, MODEL_PATH)

    return {
        "message": "Trainable email classifier was trained successfully.",
        "model_path": str(MODEL_PATH),
        "metadata": artifact["metadata"],
    }


def load_model_artifact() -> dict:
    if not MODEL_PATH.exists():
        raise ModelNotTrainedError("Trainable model has not been trained yet.")

    dependencies = import_ml_dependencies()
    return dependencies["joblib"].load(MODEL_PATH)


def get_model_status() -> dict:
    if not MODEL_PATH.exists():
        return {
            "is_trained": False,
            "model_path": str(MODEL_PATH),
            "metadata": None,
        }

    artifact = load_model_artifact()

    return {
        "is_trained": True,
        "model_path": str(MODEL_PATH),
        "metadata": artifact.get("metadata"),
    }


def predict_email_with_trained_model(email: dict) -> dict:
    artifact = load_model_artifact()
    text = build_classification_text(email)
    predictions = {}

    for target, model in artifact["models"].items():
        label = str(model.predict([text])[0])
        confidence_score = 1.0

        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba([text])[0]
            confidence_score = float(max(probabilities))

        predictions[target] = {
            "label": label,
            "confidence_score": round(confidence_score, 2),
            "evidence_terms": extract_tfidf_evidence(model, text),
        }

    return {
        "model_type": artifact["metadata"]["model_type"],
        "trained_at": artifact["metadata"]["trained_at"],
        "prediction": {
            "category": predictions["category"]["label"],
            "department": predictions["department"]["label"],
            "priority": predictions["priority"]["label"],
            "confidence_score": round(
                sum(
                    predictions[target]["confidence_score"]
                    for target in TARGET_FIELDS
                )
                / len(TARGET_FIELDS),
                2,
            ),
            "target_confidences": predictions,
            "evidence_terms": predictions["category"]["evidence_terms"],
        },
    }
