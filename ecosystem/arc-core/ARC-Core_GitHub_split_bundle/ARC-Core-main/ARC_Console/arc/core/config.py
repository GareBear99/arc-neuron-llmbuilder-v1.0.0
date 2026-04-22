from __future__ import annotations
import os
from pathlib import Path

APP_NAME = "ARC-Core"
APP_VERSION = "6.0.0"
DEMO_MODE = os.getenv("ARC_DEMO_MODE", "1") != "0"
SHARED_TOKEN = os.getenv("ARC_SHARED_TOKEN", "").strip()
DEFAULT_LIMIT = 100
MAX_LIMIT = 500
MAX_GRID_SIZE = 64
RECEIPT_VERIFY_MAX = 5000
SESSION_TTL_HOURS = int(os.getenv("ARC_SESSION_TTL_HOURS", "12"))
AUTH_BOOTSTRAP_PASSWORD = os.getenv("ARC_BOOTSTRAP_PASSWORD", "arc-demo-admin")
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
KEY_DIR = DATA_DIR / "keys"
CONNECTOR_INBOX_DIR = DATA_DIR / "connectors"
NOTEBOOK_EXPORT_LIMIT = 250
