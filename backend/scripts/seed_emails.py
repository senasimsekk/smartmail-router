import json
import sys
from pathlib import Path
from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = Path(__file__).resolve().parents[2]

sys.path.append(str(BACKEND_DIR))

from app.database import SessionLocal
from app.models.email import Email

DATA_FILE = PROJECT_DIR / "data" / "synthetic_emails.json"

def load_json_emails() -> list[dict]:
   
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)
    
def seed_emails():
    db=SessionLocal()
    
    try:
        emails = load_json_emails()

        db.execute(text("TRUNCATE TABLE email_classifications, emails RESTART IDENTITY CASCADE;"))
        db.commit()

        for email_data in emails:
            email = Email(
                subject=email_data["subject"],
                body=email_data["body"],
                sender=email_data["sender"],
                source_mailbox=email_data["source_mailbox"],
                requires_human_review=email_data.get("requires_human_review", False),
                has_attachment=email_data.get("has_attachment", False),
                attachment_names=email_data.get("attachment_names", []),
                attachment_texts=email_data.get("attachment_texts", []),
                expected_category=email_data.get("expected_category"),
                expected_department=email_data.get("expected_department"),
                expected_priority=email_data.get("expected_priority"),
            )
            db.add(email)
        db.commit()
        print(f"Seeded {len(emails)} emails into the database.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding emails: {e}")
    finally:
        db.close()  
if __name__ == "__main__":
    seed_emails()
