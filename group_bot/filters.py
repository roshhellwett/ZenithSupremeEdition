import re
import asyncio
import unicodedata
from group_bot.word_list import BANNED_WORDS, STRICT_BAD_WORDS, SPAM_DOMAINS

# 1. Strict Pattern: Matches "ass" but NOT "class"
# Uses \b (Word Boundary) on both sides
STRICT_PATTERN = re.compile(r"(?i)\b(" + "|".join(re.escape(w) for w in STRICT_BAD_WORDS) + r")\b")

# 2. Relaxed Pattern: Matches "dumbass" or "motherfucker"
# No word boundaries
RELAXED_PATTERN = re.compile(r"(?i)(" + "|".join(re.escape(w) for w in BANNED_WORDS) + r")")

def _run_regex_sync(text):
    """Zenith Deep Scan Engine: Smart Context-Aware Filtering."""
    if not text:
        return False, None

    normalized_text = unicodedata.normalize("NFKD", text).lower()
    
    if STRICT_PATTERN.search(normalized_text):
        return True, "Abusive Language Detected"

    if RELAXED_PATTERN.search(normalized_text):
        return True, "Abusive Language Detected"

    noise_free = re.sub(r'[^a-z0-9]', '', normalized_text)
    if RELAXED_PATTERN.search(noise_free):
        return True, "Attempted Profanity Bypass"

    if "makaut" not in normalized_text:
        for domain in SPAM_DOMAINS:
            if domain in normalized_text:
                return True, "Unauthorized Link"

    return False, None

async def is_inappropriate(text: str) -> (bool, str):
    """Asynchronous wrapper for the forensic scanner."""
    if not text:
        return False, None
    return await asyncio.to_thread(_run_regex_sync, text)
    #@academictelebotbyroshhellwett