import os
from pathlib import Path

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Default DB Path: /app/data/stockpilot.db in Docker, or local ./data/stockpilot.db
def get_default_db_path() -> str:
    if os.path.exists("/.dockerenv") or os.environ.get("IS_DOCKER") == "true":
        return "/app/data/stockpilot.db"
    return str(BASE_DIR / "data" / "stockpilot.db")

DB_PATH = os.getenv("DB_PATH", get_default_db_path())
PORT = int(os.getenv("PORT", "5000"))
HOST = os.getenv("HOST", "0.0.0.0")
SECRET_KEY = os.getenv("SECRET_KEY", "stockpilot-secret-key-change-in-production")

# Ensure directory for DB exists
db_parent = os.path.dirname(os.path.abspath(DB_PATH))
if db_parent:
    os.makedirs(db_parent, exist_ok=True)
