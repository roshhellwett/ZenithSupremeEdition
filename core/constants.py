# Zenith Supreme Constants Registry
# Network Identities (Centralized)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Forensic Scraper Blocklist
NOISE_TITLES = ["about us", "contact", "home", "back", "gallery", "tender", "bid"]

# Category Mapping for Icon Assignment
CATEGORY_ICONS = {
    "URGENT": "🚨",
    "RESULT": "🏆",
    "EXAM": "📝",
    "FORM": "✍️",
    "ADMISSION": "🎓",
    "VACANCY": "💼",
    "DEFAULT": "📌"
}

# Keywords for classification
KEYWORDS = {
    "URGENT": ["urgent", "postponed", "cancelled", "alert"],
    "RESULT": ["result", "mark", "grade", "score"],
    "EXAM": ["exam", "schedule", "routine", "ca1", "ca2", "pca"],
    "FORM": ["form", "enrollment", "registration"],
    "ADMISSION": ["admission", "ph.d", "course"],
    "VACANCY": ["vacanc", "recruit", "job"]
}

# UI Strings for Search Bot
SEARCH_FILTERS = [["/latest", "BCA", "CSE"], ["Exam", "Result", "Form"]]
#@academictelebotbyroshhellwett