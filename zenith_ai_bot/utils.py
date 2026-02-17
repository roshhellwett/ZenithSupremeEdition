import re
import asyncio
from cachetools import TTLCache
from sqlalchemy import text
from core.logger import setup_logger

logger = setup_logger("AI_UTILS")
ai_rate_limit = TTLCache(maxsize=10000, ttl=60.0)
_ai_db_engine = None

async def get_db_engine():
    global _ai_db_engine
    if _ai_db_engine is None:
        from core.config import DATABASE_URL
        if DATABASE_URL:
            from sqlalchemy.ext.asyncio import create_async_engine
            _ai_db_engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)
    return _ai_db_engine

async def dispose_db_engine():
    global _ai_db_engine
    if _ai_db_engine:
        await _ai_db_engine.dispose()
        _ai_db_engine = None

async def check_user_ban_status(user_id: int) -> bool:
    try:
        engine = await get_db_engine()
        if not engine: return False
        
        async def fetch_db():
            async with engine.connect() as conn:
                query = text("SELECT strike_count FROM zenith_group_strikes WHERE user_id = :uid AND strike_count >= 3 LIMIT 1")
                result = await conn.execute(query, {"uid": user_id})
                return result.scalar() is not None
        
        return await asyncio.wait_for(fetch_db(), timeout=5.0)
    except asyncio.TimeoutError:
        logger.warning("⚠️ DB Fallback: Connection Timeout.")
        return False
    except Exception as e:
        logger.warning(f"⚠️ DB Fallback Triggered: {repr(e)}")
        return False

async def check_ai_rate_limit(user_id: int) -> tuple[bool, str]:
    if await check_user_ban_status(user_id):
        return False, "🚫 You are globally banned from Zenith services due to group violations."

    current_requests = ai_rate_limit.get(user_id, 0)
    if current_requests >= 5:
        return False, "⏳ You are requesting too fast! Zenith AI needs a moment to rest. Please wait 60 seconds."
    
    ai_rate_limit[user_id] = current_requests + 1
    return True, ""

def sanitize_telegram_html(raw_text: str) -> str:
    if not raw_text: return ""
    txt = raw_text
    
    # Strip markdown code block wrappers if LLM hallucinated them
    if txt.startswith("```html"): txt = txt[7:]
    elif txt.startswith("```"): txt = txt[3:]
    if txt.endswith("```"): txt = txt[:-3]
    
    # Convert markdown bold to HTML bold safely
    txt = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", txt)
    
    # Replace <br> with newline before stripping
    txt = re.sub(r"<br\s*/?>", "\n", txt, flags=re.IGNORECASE)
    
    # Replace block-level tags with newlines before stripping
    txt = re.sub(r"<img[^>]*>", "[Image Omitted]", txt, flags=re.IGNORECASE)
    
    # Allowlist approach: only keep Telegram-safe tags, strip everything else
    # Allowed: <b>, <i>, <u>, <s>, <code>, <pre>, <a href="...">
    allowed_pattern = re.compile(
        r'<(?!'
        r'/?b>|/?i>|/?u>|/?s>|/?code>|/?pre>|'
        r'a\s+href=["\'][^"\']*["\'][^>]*>|/a>'
        r')[^>]*>',
        re.IGNORECASE
    )
    txt = allowed_pattern.sub("", txt)
    
    # Clean up massive gaps created by stripping tags
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    
    return txt.strip()