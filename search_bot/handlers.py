from database.db import SessionLocal
from database.models import Notification
from pipeline.message_formatter import format_search_result

def get_latest_results(limit=10):
    """Fetches the 10 most recent notices sorted by their actual publication date."""
    db = SessionLocal()
    try:
        # Sort by published_date descending (Newest first)
        notices = db.query(Notification).order_by(Notification.published_date.desc()).limit(limit).all()
        return format_search_result(notices)
    finally:
        db.close()

def search_by_keyword(query, limit=10):
    """Searches for keywords and returns results sorted by date."""
    db = SessionLocal()
    try:
        # Uses ILIKE for case-insensitive keyword search
        results = db.query(Notification).filter(
            Notification.title.ilike(f"%{query}%")
        ).order_by(Notification.published_date.desc()).limit(limit).all()
        return format_search_result(results)
    finally:
        db.close()