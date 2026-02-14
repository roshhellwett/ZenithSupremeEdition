import httpx
import random
import logging
import asyncio
import time
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

from utils.hash_util import generate_hash
from core.sources import URLS
from core.config import SSL_VERIFY_EXEMPT, TARGET_YEARS, REQUEST_TIMEOUT
from scraper.date_extractor import extract_date
from scraper.pdf_processor import get_date_from_pdf

logger = logging.getLogger("SCRAPER")

# Robust User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/121.0.0.0 Safari/537.36"
]

# CIRCUIT BREAKER STATE
source_health = {}
MAX_FAILURES = 3
COOLDOWN_SECONDS = 1800  # 30 Minutes

def _parse_html_sync(html_content, source_config):
    """
    CPU-BOUND TASK: Universal Link Extractor with Strict Isolation.
    Prevents cross-contamination from adjacent links.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    items = []
    
    for a in soup.find_all("a", href=True):
        full_url = urljoin(source_config["url"], a["href"])
        link_text = a.get_text(" ", strip=True)
        
        # SMART ISOLATION: 
        # Only use parent text if this is the ONLY link inside the parent (e.g., a single <li>)
        parent_text = ""
        if a.parent and len(a.parent.find_all("a")) == 1:
            parent_text = a.parent.get_text(" ", strip=True)
            
        if parent_text and len(parent_text) < 300:
            final_text = parent_text
        else:
            # If parent is a massive container, fallback to ONLY the text immediately before the link
            prev = a.previous_sibling
            # Check if previous sibling is a raw text string, not another HTML tag
            prev_text = str(prev).strip() if prev and getattr(prev, 'name', None) is None else ""
            final_text = f"{prev_text} {link_text}".strip() if len(prev_text) < 50 else link_text
        
        items.append({
            "text": final_text,
            "url": full_url
        })
            
    return items

async def build_item(raw_data, source_name):
    """Async Processor for individual items."""
    title = raw_data["text"]
    url = raw_data["url"]

    if not title or not url: return None
    
    # 1. Forensic Noise Filtering
    BLOCKLIST = ["about us", "contact", "home", "back", "gallery", "archive", "click here", "apply now", "visit", "syllabus"]
    if len(title) < 5 or any(k in title.lower() for k in BLOCKLIST): 
        return None

    # 2. STRICT Date Discovery (Title ONLY - Context is already merged)
    real_date = extract_date(title) 
    
    # 🚨 THE ABSOLUTE SHIELD: No Date? DROP IT.
    if not real_date:
        return None

    # 3. Refined GHOST FILTER
    OLD_YEARS = ["2019", "2020", "2021", "2022", "2023"]
    if any(y in title for y in OLD_YEARS):
        # If extracted date is old, DROP IT.
        if str(real_date.year) in OLD_YEARS:
            return None

    # 4. Validity Check (Dynamic Year Window)
    if real_date and real_date.year in TARGET_YEARS:
        return {
            "title": title.strip(),
            "source": source_name,
            "source_url": url,
            "pdf_url": url if ".pdf" in url.lower() else None,
            "content_hash": generate_hash(title, url),
            "published_date": real_date,
            "scraped_at": datetime.utcnow()
        }
    
    return None

async def scrape_source(source_key, source_config):
    # --- CIRCUIT BREAKER CHECK ---
    health = source_health.get(source_key, {"fails": 0, "next_try": 0})
    if time.time() < health["next_try"]:
        return []

    headers = {"User-Agent": random.choice(USER_AGENTS)}
    verify = not any(domain in source_config["url"] for domain in SSL_VERIFY_EXEMPT)
    
    try:
        await asyncio.sleep(random.uniform(2, 5)) 
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, verify=verify, follow_redirects=True) as client:
            r = await client.get(source_config["url"], headers=headers)
            r.raise_for_status()

            raw_items = await asyncio.to_thread(_parse_html_sync, r.text, source_config)
            
            logger.info(f"🔎 {source_key}: Analyzing {len(raw_items)} candidates...")
            
            valid_items = []
            for raw in raw_items:
                item = await build_item(raw, source_config["source"])
                if item: valid_items.append(item)

            source_health[source_key] = {"fails": 0, "next_try": 0}
            
            if valid_items:
                logger.info(f"✅ {source_key}: Extracted {len(valid_items)} valid notices.")
            return valid_items

    except Exception as e:
        fails = health["fails"] + 1
        wait_time = 0
        if fails >= MAX_FAILURES:
            wait_time = COOLDOWN_SECONDS
            logger.error(f"❌ {source_key} BROKEN: {e}. Cooling down for {wait_time}s.")
        else:
            logger.warning(f"⚠️ {source_key} Glitch: {e}")

        source_health[source_key] = {
            "fails": fails, 
            "next_try": time.time() + wait_time
        }
        return []
#@academictelebotbyroshhellwett