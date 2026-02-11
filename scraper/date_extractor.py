import re
from datetime import datetime

# Optimized to be more flexible with spaces and prefixes
DATE_PATTERNS = [
    r"\d{2}[-/\.]\d{2}[-/\.]\d{4}",  # DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
    r"\d{4}[-/\.]\d{2}[-/\.]\d{2}",  # YYYY-MM-DD
    r"Dated?[:\s]*\d{2}[-/\.]\d{2}[-/\.]\d{4}" # Flexible for "Dated:22.11.2019"
]

def extract_date(text: str):
    if not text:
        return None

    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Strip "Dated" text and any colons/spaces
            date_str = re.sub(r"Dated?[:\s]*", "", match.group(), flags=re.IGNORECASE)
            
            # Normalize all separators to "/"
            normalized = date_str.replace("-", "/").replace(".", "/")
            
            for fmt in ("%d/%m/%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(normalized, fmt)
                except ValueError:
                    continue
    return None