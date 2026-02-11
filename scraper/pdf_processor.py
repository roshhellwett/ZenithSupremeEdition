import io
import pdfplumber
import requests
import logging
from scraper.date_extractor import extract_date

logger = logging.getLogger("PDF_PROCESSOR")

def get_date_from_pdf(pdf_url):
    try:
        response = requests.get(pdf_url, timeout=15, stream=True, verify=False)
        content = response.raw.read(102400) # Read only the first 100KB for speed
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            first_page = pdf.pages[0]
            width, height = first_page.width, first_page.height
            
            # 1. PRIORITY: TOP RIGHT (where official dates like "Dated: 22.11.2019" appear)
            # Box: (left, top, right, bottom) - Top 25%, Right 50%
            top_right_box = (width * 0.5, 0, width, height * 0.25)
            top_right_text = first_page.within_bbox(top_right_box).extract_text()
            date = extract_date(top_right_text)
            if date: return date

            # 2. SECONDARY: BOTTOM SIGNATURE AREA (Bottom 15%)
            bottom_box = (0, height * 0.85, width, height)
            bottom_text = first_page.within_bbox(bottom_box).extract_text()
            date = extract_date(bottom_text)
            if date: return date

            # 3. FALLBACK: Full Page Search
            return extract_date(first_page.extract_text())
            
    except Exception as e:
        logger.warning(f"Could not read PDF {pdf_url}: {e}")
        return None