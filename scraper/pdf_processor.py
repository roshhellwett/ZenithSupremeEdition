import logging
import pdfplumber
import requests
import io
from scraper.date_extractor import extract_date

logger = logging.getLogger("PDF_PROCESSOR")

def get_date_from_pdf(pdf_url):
    """
    Zenith PDF Forensic Scan:
    1. Checks Metadata (CreationDate) as the fastest verification.
    2. Crops the page to scan the Header (Visual Priority) to ignore table dates.
    3. Falls back to Full-Text scan if the header is empty.
    """
    try:
        # Uses standard requests; User-Agent rotation is handled in the main scraper [cite: 17, 27]
        response = requests.get(pdf_url, timeout=15, verify=False) 
        if response.status_code != 200: 
            return None
            
        pdf_bytes = io.BytesIO(response.content)

        with pdfplumber.open(pdf_bytes) as pdf:
            if not pdf.pages:
                return None
                
            p = pdf.pages[0]
            
            # --- PHASE 1: METADATA CHECK (Digital Signature) ---
            meta_date = pdf.metadata.get('CreationDate')
            if meta_date and "2026" in meta_date:
                # Format: D:20260212... [cite: 28, 29]
                try:
                    from datetime import datetime
                    return datetime.strptime(meta_date[2:10], "%Y%m%d")
                except: 
                    pass

            # --- PHASE 2: VISUAL HEADER SCAN (Top 25%) ---
            # Most university notice dates are at the top-right or top-left
            width = p.width
            height = p.height
            header_area = (0, 0, width, height * 0.25)
            
            try:
                # Extract text ONLY from the top quarter of the page [cite: 30]
                header_text = p.within_bbox(header_area).extract_text()
                header_date = extract_date(header_text)
                if header_date:
                    return header_date # High-Confidence result
            except:
                pass

            # --- PHASE 3: FULL PAGE FALLBACK ---
            # If the header scan fails, scan the entire page but prioritize the first match
            full_text = p.extract_text()
            return extract_date(full_text)

    except Exception as e:
        logger.error(f"❌ Zenith PDF Forensic Error: {e}")
        
    return None