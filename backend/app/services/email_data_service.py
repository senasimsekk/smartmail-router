from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parents[3]
DATA_FILE = BASE_DIR / "data" / "synthetic_emails.json"


def load_emails() -> list[dict]:
    """
    Sentetik e-posta veri setini JSON dosyasından okur.
    """

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)