import logging
import pdfplumber
import httpx
import io
import asyncio
import random
from datetime import datetime
from scraper.date_extractor import extract_date
from core.config import SSL_VERIFY_EXEMPT, REQUEST_TIMEOUT, MAX_PDF_SIZE_MB

logger = logging.getLogger("PDF_PROC")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

def _parse_pdf_sync(pdf_bytes):
    """CPU-bound parsing (Sync). Runs in thread."""
    try:
        with pdfplumber.open(pdf_bytes) as pdf:
            if not pdf.pages: return None
            
            # 1. Metadata Scan
            meta = pdf.metadata.get('CreationDate')
            if meta:
                clean = meta.replace("D:", "")[:8]
                return datetime.strptime(clean, "%Y%m%d")

            # 2. Text Scan (Page 1)
            text = pdf.pages[0].extract_text()
            return extract_date(text)
    except Exception:
        return None

async def get_date_from_pdf(pdf_url):
    """
    Memory-Safe PDF Fetcher.
    Streams data and aborts if file is too large.
    """
    verify = not any(d in pdf_url for d in SSL_VERIFY_EXEMPT)
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    try:
        async with httpx.AsyncClient(verify=verify, timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            async with client.stream("GET", pdf_url, headers=headers) as response:
                if response.status_code != 200: return None
                
                # Check Size Header First
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > (MAX_PDF_SIZE_MB * 1024 * 1024):
                    return None

                # Safe Stream Download
                data = io.BytesIO()
                downloaded = 0
                max_bytes = MAX_PDF_SIZE_MB * 1024 * 1024

                async for chunk in response.aiter_bytes():
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        logger.warning(f"⚠️ PDF truncated (Too Large): {pdf_url}")
                        return None # Abort download
                    data.write(chunk)
                
                data.seek(0)
                
                # Offload CPU work to thread
                return await asyncio.to_thread(_parse_pdf_sync, data)

    except Exception as e:
        logger.debug(f"⚠️ PDF Skip: {e}")
        return None
        #@academictelebotbyroshhellwett