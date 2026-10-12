"""Central settings for the Campus Customs backend.

MODEL_NAME is defined here and nowhere else. Every other file imports it.
The Portkey key is read from .env at run time and is never printed or logged.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import UsageLimits

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep console output readable

# ---- Model (the ONLY place the model name is written) ----
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# ---- Paths ----
ORIGINAL_DB = PROJECT_ROOT / "data" / "campus_customs.db"
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"
MCP_SERVER_SCRIPT = PROJECT_ROOT / "mcp_server" / "server.py"
PROMPTS_DIR = PROJECT_ROOT / "backend" / "prompts"
AUDIT_TRAIL = PROJECT_ROOT / "output" / "audit_trail.json"

# ---- Guardrails ----
MAX_DELEGATION_DEPTH = 3

# Tools that move money, decide approvals, or set up tables. Hidden from every agent;
# only the backend routes may call them.
BACKEND_ONLY_TOOLS = frozenset({"execute_approved_payment", "reject_approval", "init_helper_tables"})

# Per-run limits shared by the whole team (one usage object per run).
DEFAULT_REQUEST_LIMIT = 60
DEFAULT_TOOL_CALLS_LIMIT = 80
DEFAULT_TOTAL_TOKENS_LIMIT = 400_000


def default_usage_limits() -> UsageLimits:
    return UsageLimits(
        request_limit=DEFAULT_REQUEST_LIMIT,
        tool_calls_limit=DEFAULT_TOOL_CALLS_LIMIT,
        total_tokens_limit=DEFAULT_TOTAL_TOKENS_LIMIT,
    )


def get_portkey_api_key() -> str:
    """Return the Portkey key from .env. Raises (without echoing anything) if missing."""
    key = os.environ.get("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to hw5/.env (see .env.example).")
    return key
