import re
import unicodedata
from datetime import datetime

# Zenith Regex: Prioritizes dates following "Anchor" words common in university notices
# This prevents picking up 'Deadline' dates or 'Table' dates by mistake.
ANCHOR_PATTERN = r"(?i)(?:dated?|no|kolkata|issue|on)\s*[:\-]?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})"
FALLBACK_PATTERN = r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})"

def extract_date(text: str):
    """
    Zenith Date Extractor: Uses Anchor Weighting to find the true issuance date.
    Normalizes unicode to fix '2 0 2 6' artifacts common in bad PDF layers.
    """
    if not text:
        return None
    
    # Normalize unicode (NFKD) and collapse extra spaces to fix broken text artifacts [cite: 14, 15]
    clean_text = unicodedata.normalize("NFKD", text)
    clean_text = " ".join(clean_text.split()).strip()

    # 1. High-Confidence: Try Anchor Pattern First (e.g., "Dated: 12/02/2026")
    match = re.search(ANCHOR_PATTERN, clean_text)
    
    # 2. Fallback: If no anchors found, take the first valid date string
    if not match:
        match = re.search(FALLBACK_PATTERN, clean_text)
        
    if match:
        # Extract the date group
        date_str = match.group(1) if len(match.groups()) > 0 else match.group(0)
        
        # Standardize separators for the datetime parser [cite: 15]
        normalized = date_str.replace("-", "/").replace(".", "/")
        
        # Strip ordinals (e.g., 12th -> 12) to ensure strptime doesn't fail
        normalized = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", normalized, flags=re.I)
        
        # Waterfall parsing across common formats used in India
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d/%b/%Y"):
            try:
                dt = datetime.strptime(normalized, fmt)
                # 🛡️ THE GATEKEEPER: Strictly only 2026 notices [cite: 16, 21]
                if dt.year == 2026:
                    return dt
            except ValueError:
                continue
                
    return None