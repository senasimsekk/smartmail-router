import sys
from pathlib import Path

from sqlalchemy import text


backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

from app.database import engine

def create_system_logs_table():
    with engine.connect() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS system_logs (
                    id SERIAL PRIMARY KEY,
                    email_id INTEGER REFERENCES emails(id) ON DELETE SET NULL,
                    action_type VARCHAR(100) NOT NULL,
                    action_detail TEXT,
                    actor VARCHAR(100) DEFAULT 'system',
                    status VARCHAR(50) DEFAULT 'success',
                    extra_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )

        connection.commit()

    print("system_logs table was created successfully.")


if __name__ == "__main__":
    create_system_logs_table()
