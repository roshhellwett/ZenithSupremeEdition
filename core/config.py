import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ==============================
# TELEGRAM TOKENS & SECURITY
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SEARCH_BOT_TOKEN = os.getenv("SEARCH_BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
GROUP_BOT_TOKEN = os.getenv("GROUP_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN:
    raise ValueError("❌ FATAL: BOT_TOKEN is missing from Environment Variables.")

# ==============================
# CLOUD DATABASE CONFIGURATION
# ==============================
_RAW_DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///local_backup.db")

if _RAW_DB_URL.startswith("postgres://"):
    DATABASE_URL = _RAW_DB_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif _RAW_DB_URL.startswith("postgresql://"):
    DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = _RAW_DB_URL

# ==============================
# PIPELINE SETTINGS
# ==============================
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "300"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# DYNAMIC YEAR LOGIC:
# Automatically accepts notices from the current year AND the previous year
# (e.g., In 2026, it accepts 2026 and 2025 to cover academic sessions)
CURRENT_YEAR = datetime.now().year
TARGET_YEARS = [CURRENT_YEAR, CURRENT_YEAR - 1]

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ==============================
# PERFORMANCE & LIMITS
# ==============================
SSL_VERIFY_EXEMPT = ["makautexam.net", "www.makautexam.net"]
REQUEST_TIMEOUT = 30.0
MAX_PDF_SIZE_MB = 10  # Max size to download
DB_POOL_SIZE = 5      # Safe limit for Railway Starter Plan
DB_MAX_OVERFLOW = 10  # Burst buffer
#@academictelebotbyroshhellwett