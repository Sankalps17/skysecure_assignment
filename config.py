"""Application configuration — environment variables, constants, and logging setup."""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

# ── Zoho OAuth ──
ZOHO_CLIENT_ID: str = os.getenv("ZOHO_CLIENT_ID", "")
ZOHO_CLIENT_SECRET: str = os.getenv("ZOHO_CLIENT_SECRET", "")
ZOHO_REDIRECT_URI: str = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:8501")
ZOHO_DOMAIN: str = os.getenv("ZOHO_DOMAIN", ".com")

ZOHO_SCOPES: list[str] = [
    "ZohoProjects.portals.READ",
    "ZohoProjects.projects.READ",
    "ZohoProjects.tasks.READ",
    "ZohoProjects.tasks.CREATE",
    "ZohoProjects.tasks.UPDATE",
    "ZohoProjects.tasks.DELETE",
    "ZohoProjects.milestones.READ",
    "ZohoProjects.users.READ",
    "ZohoProjects.timesheets.READ",
]

# ── Google Gemini ──
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# ── OpenAI (alternative provider) ──
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# ── LLM Provider selection: "gemini" (default) or "openai" ──
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("skysec")
