import requests
import random
import logging
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

from utils.hash_util import generate_hash
from core.sources import URLS
from scraper.date_extractor import extract_date
from scraper.pdf_processor import get_date_from_pdf

# Suppress SSL warnings for university sites with expired/invalid certs [cite: 18]
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger("SCRAPER")

# --- SUPREME GOD MODE: USER-AGENT POOL ---
# Rotates identity to prevent university firewalls from blocking your laptop IP
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
]

SESSION = requests.Session()

# --- SUPREME GOD MODE: HEALTH TRACKER ---
# Tracks consecutive failures per source for the Admin Alert system
source_health = {key: 0 for key in URLS.keys()}

def get_source_health():
    """Returns the current failure counts for all monitored sources."""
    return source_health

def build_item(title, url, source_name, date_context=None):
    """
    STRICT 2026 GATEKEEPER:
    Validates notices against the year 2026 before storage[cite: 89, 90].
    """
    if not title or not url: 
        return None
    
    # 1. Standard Noise Filtering [cite: 18]
    # Uses the blocklist to ignore static menu items like 'Home' or 'Contact'
    STRICT_BLOCKLIST = [
        "about us", "contact", "directory", "staff", "genesis", "vision", 
        "mission", "campus", "library", "login", "register", "sitemap", 
        "disclaimer", "university", "chancellor", "vice-chancellor", "registrar",
        "home", "administration", "committees", "affiliated", "regulations", 
        "academics", "schools", "programmes", "syllabus", "calendar", "moocs", 
        "ph.d.", "aicte", "ugc", "mhrd", "aishe", "nptel", "swayam", "fee", 
        "scholarship", "entrance", "happening", "seminar", "workshop", "events", 
        "students", "placements", "results", "alumni", "gallery", "hostel", "sports"
    ]
    
    if any(k in title.lower() for k in STRICT_BLOCKLIST):
        return None

    # 2. Date Verification (Title & Context) [cite: 20]
    real_date = extract_date(title)
    if not real_date and date_context:
        real_date = extract_date(date_context)
    
    # 3. Date Verification (PDF Deep Scan) [cite: 21]
    if not real_date and ".pdf" in url.lower():
        real_date = get_date_from_pdf(url)

    # 4. Final Year Validation [cite: 22]
    # Discards anything that isn't confirmed for 2026 [cite: 92]
    if real_date and real_date.year == 2026:
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

def parse_generic_links(base_url, source_name):
    """Scrapes links from a given URL using rotated User-Agents."""
    data = []
    seen = set()
    verify_ssl = False if "makautexam" in base_url else True
    
    # Supreme Identity Rotation
    SESSION.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    
    try:
        r = SESSION.get(base_url, timeout=30, verify=verify_ssl)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Locate main content area [cite: 23]
        main_body = soup.find("div", {"id": "content"}) or soup.find("div", class_="content") or soup.find("table") or soup
        
        for a in main_body.find_all("a"):
            title = a.get_text(" ", strip=True)
            href = a.get("href")
            if not title or not href: continue
            
            full_url = urljoin(base_url, href)
            if not full_url.startswith(("http:", "https:")): continue
            
            h = generate_hash(title, full_url)
            if h in seen: continue
            seen.add(h)

            item = build_item(title, full_url, source_name, a.parent.get_text(" ", strip=True) if a.parent else "")
            if item:
                data.append(item)
    except Exception as e:
        # Pass exception up to scrape_source for health tracking
        raise e
    return data

def scrape_source(source_key, source_config):
    """
    Orchestrates the scrape and manages the source health counter.
    """
    url = source_config["url"]
    source_name = source_config["source"]
    
    try:
        results = parse_generic_links(url, source_name)
        # Reset failure count on successful scrape
        source_health[source_key] = 0 
        return results
    except Exception as e:
        # Increment failure count for the specific source
        source_health[source_key] += 1
        logger.warning(f"⚠️ {source_key} Health Drop ({source_health[source_key]}): {e}")
        return []

def scrape_all_sources():
    """Main entry point to cycle through all configured URLs[cite: 27]."""
    all_data = []
    for key, config in URLS.items():
        logger.info(f"SCRAPING SOURCE: {key}")
        source_data = scrape_source(key, config)
        all_data.extend(source_data)
    return all_data