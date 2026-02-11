import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import time
from urllib.parse import urljoin
import urllib3

from utils.hash_util import generate_hash
from core.sources import URLS
from scraper.date_extractor import extract_date
from scraper.pdf_processor import get_date_from_pdf  # New logic

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger("SCRAPER")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
})

STRICT_BLOCKLIST = [
    "about us", "contact", "directory", "staff", "genesis", "vision", 
    "mission", "campus", "library", "login", "register", "sitemap", 
    "disclaimer", "university", "chancellor", "vice-chancellor", "registrar",
    "convocation", "antiragging", "rti", "forms", "archive", "tenders",
    "defaulter", "ordinance", "statutes", "officers", "recognition"
]

MENU_BUTTON_TERMS = [
    "administration", "committees", "affiliated", "academics", 
    "rules", "regulations", "right to information", "governance", "act"
]

def build_item(title, url, source_name, date_context=None):
    if not title or not url:
        return None
    
    title_lower = title.strip().lower()

    # Filters based on your previous logs and screenshots
    if any(k in title_lower for k in STRICT_BLOCKLIST):
        return None
        
    if any(k in title_lower for k in MENU_BUTTON_TERMS):
        if len(title) < 25: 
            return None

    if len(title) < 5:
        return None

    if any(x in url.lower() for x in ["javascript", "mailto", "tel:", "#"]):
        return None

    # --- DATE EXTRACTION LOGIC ---
    # 1. Try Title and Context first
    real_date = extract_date(title)
    if not real_date and date_context:
        real_date = extract_date(date_context)

    # 2. Deep PDF Scan if still no date
    is_pdf = ".pdf" in url.lower()
    if is_pdf and not real_date:
        logger.info(f"Deep scanning PDF for date: {title}")
        real_date = get_date_from_pdf(url)

    # 3. Fallback to current time if all else fails
    if not real_date:
        real_date = datetime.utcnow()

    return {
        "title": title.strip(),
        "source": source_name,
        "source_url": url,
        "pdf_url": url if is_pdf else None,
        "content_hash": generate_hash(title, url),
        "published_date": real_date,
        "scraped_at": datetime.utcnow()
    }

def parse_generic_links(base_url, source_name):
    data = []
    seen = set()
    verify_ssl = False if "makautexam" in base_url else True
    
    try:
        r = SESSION.get(base_url, timeout=30, verify=verify_ssl)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        main_body = soup.find("div", {"id": "content"}) or soup.find("div", class_="content") or soup.find("table") or soup
        
        for a in main_body.find_all("a"):
            title = a.get_text(" ", strip=True)
            href = a.get("href")
            if not title or not href: continue

            full_url = urljoin(base_url, href)
            if not full_url.startswith(("http:", "https:")): continue
            
            context_text = a.parent.get_text(" ", strip=True) if a.parent else ""
            h = generate_hash(title, full_url)
            if h in seen: continue
            seen.add(h)

            item = build_item(title, full_url, source_name, context_text)
            if item:
                data.append(item)
    except Exception as e:
        raise e
    return data

def scrape_source(source_key, source_config):
    url = source_config["url"]
    source_name = source_config["source"]
    for attempt in range(3):
        try:
            return parse_generic_links(url, source_name)
        except Exception as e:
            logger.warning(f"{source_key} attempt {attempt+1}/3 failed: {e}")
            time.sleep(2)
    return []

def scrape_all_sources():
    all_data = []
    for key, config in URLS.items():
        logger.info(f"SCRAPING SOURCE {key}")
        source_data = scrape_source(key, config)
        all_data.extend(source_data)
    return all_data