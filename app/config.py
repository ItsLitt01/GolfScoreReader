"""Load .env and expose app/config constants."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(BASE_DIR, ".env")


def _load_dotenv_manual() -> None:
    """Load .env into os.environ (fallback if python-dotenv not used or failed)."""
    if not os.path.isfile(_ENV_PATH):
        return
    with open(_ENV_PATH, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"").strip()
                if key and value:
                    os.environ.setdefault(key, value)


try:
    from dotenv import load_dotenv
    load_dotenv(_ENV_PATH)
except ImportError:
    pass
_load_dotenv_manual()


APP_NAME = "FairwAI"
APP_VERSION = "0.4.0"

GEMINI_MODEL_ORDER = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

# Resize image
MAX_IMAGE_DIMENSION = int(os.environ.get("MAX_IMAGE_DIMENSION", "1536"))
