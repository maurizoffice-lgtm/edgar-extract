"""Central settings: project paths and values from the .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv

# src/edgar_extract/config.py -> project root is two levels above src/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
REPORTS_DIR = PROJECT_ROOT / "reports"

load_dotenv(PROJECT_ROOT / ".env")


def get_sec_user_agent() -> str:
    """Return the User-Agent the SEC requires (name + email), from .env."""
    user_agent = os.getenv("SEC_USER_AGENT", "").strip()
    if not user_agent or "example.com" in user_agent or "@" not in user_agent:
        raise RuntimeError(
            "SEC_USER_AGENT is missing or still the placeholder. "
            'Set it in .env, e.g. SEC_USER_AGENT="Jane Doe jane@example.org"'
        )
    return user_agent
