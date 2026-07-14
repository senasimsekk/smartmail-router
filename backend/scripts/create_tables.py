

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

print("Script started")

from app.database import Base, engine
from app.models.email import Email
from app.models.email_classification import EmailClassification
from app.models.feedback import Feedback
from app.models.system_log import SystemLog
def create_tables():
    print("Registered tables:", Base.metadata.tables.keys())

    Base.metadata.create_all(bind=engine)

    print("Database tables created successfully.")


if __name__ == "__main__":
    create_tables()