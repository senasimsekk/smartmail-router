import sys
from pathlib import Path

from sqlalchemy import text

backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

from app.database import engine


def add_routing_fields():
    with engine.connect() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE emails
                ADD COLUMN IF NOT EXISTS routing_status VARCHAR(50) DEFAULT 'New',
                ADD COLUMN IF NOT EXISTS approved_department VARCHAR(100),
                ADD COLUMN IF NOT EXISTS approved_by VARCHAR(100),
                ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP,
                ADD COLUMN IF NOT EXISTS routing_note TEXT;
                """
            )
        )

        connection.commit()

    print("Routing fields were added successfully.")


if __name__ == "__main__":
    add_routing_fields()