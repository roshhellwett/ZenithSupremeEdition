import re
import asyncio
import unicodedata
from group_bot.word_list import BANNED_WORDS, SPAM_DOMAINS

# UPGRADE: Pre-compile pattern once to save CPU cycles during high traffic
ABUSE_PATTERN = re.compile(r"(?i)\b(" + "|".join(re.escape(word) for word in BANNED_WORDS) + r")\b")

def _run_regex_sync(text):
    """Zenith Deep Scan Engine: Optimized with pre-compiled patterns."""
    if not text:
        return False, None

    normalized_text = unicodedata.normalize("NFKD", text).lower()
    
    # 1. De-Noising
    noise_free = re.sub(r'[^a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s]', '', normalized_text)
    collapsed_text = noise_free.replace(" ", "")

    # 2. Forensic Match (Using pre-compiled engine)
    if ABUSE_PATTERN.search(collapsed_text):
        return True, "Abusive/Inappropriate Language"

    # 3. Smart Link Protection
    if "makaut" not in normalized_text:
        for domain in SPAM_DOMAINS:
            if domain in normalized_text:
                return True, "Unauthorized/Suspicious Link"

    return False, None

async def is_inappropriate(text: str) -> (bool, str):
    if not text:
        return False, None
    return await asyncio.to_thread(_run_regex_sync, text)
#@academictelebotbyroshhellwett