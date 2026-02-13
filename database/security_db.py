import logging
from database.db import engine, AsyncSessionLocal, Base

# =================================================================
# ⚠️ DEPRECATED MODULE
# This file exists only for backward compatibility during migration.
# It redirects all calls to the main PostgreSQL engine in database.db.
# =================================================================

logger = logging.getLogger("SECURITY_DB_LEGACY")
logger.warning("⚠️ LEGACY IMPORT: database.security_db is deprecated. Redirecting to main PostgreSQL engine.")

# Redirect legacy objects to the new unified PostgreSQL connection
# This prevents "No module named 'aiosqlite'" errors.
security_engine = engine
SecuritySessionLocal = AsyncSessionLocal
SecurityBase = Base