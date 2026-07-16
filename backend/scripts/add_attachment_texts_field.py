import sys
from pathlib import Path

from sqlalchemy import text

backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

from app.database import engine


def add_attachment_texts_field():
    with engine.connect() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE emails
                ADD COLUMN IF NOT EXISTS attachment_texts JSON DEFAULT '[]'::json;
                """
            )
        )
        connection.commit()

    print("Attachment texts field was added successfully.")


if __name__ == "__main__":
    add_attachment_texts_field()
