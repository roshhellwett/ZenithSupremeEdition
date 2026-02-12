from datetime import datetime

def _format_date(value):
    if not value: return None
    if isinstance(value, datetime): return value.strftime("%d %b %Y")
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed.strftime("%d %b %Y")
    except: return None

def get_category_icon(title):
    t = title.lower()
    # [cite_start]God Mode Priority Detection [cite: 117]
    if any(k in t for k in ["urgent", "postponed", "cancelled", "alert"]): return "🚨"
    if any(k in t for k in ["result", "mark", "grade", "score"]): return "🏆"
    if any(k in t for k in ["exam", "schedule", "routine", "ca1", "ca2", "pca"]): return "📝"
    if any(k in t for k in ["form", "enrollment", "registration"]): return "✍️"
    if any(k in t for k in ["admission", "ph.d", "course"]): return "🎓"
    if any(k in t for k in ["vacanc", "recruit", "job"]): return "💼"
    return "📌"

def format_message(n):
    title = n.get("title", "No Title").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    url = n.get("source_url", "")
    source = n.get("source", "MAKAUT")
    is_pdf = n.get("pdf_url") is not None
    icon = get_category_icon(title)
    
    # Supreme God Mode: Auto-highlight Urgent Notices
    is_urgent = icon == "🚨"
    header = f"{icon} <b>URGENT {source} NOTICE</b>" if is_urgent else f"{icon} <b>{source}</b>"
    action_text = "📄 Download PDF" if is_pdf else "🔗 Open Link"
    
    return (
        f"{header} | {'PDF Document' if is_pdf else 'Web Link'}\n\n"
        f"<b>{title}</b>\n\n"
        f"<a href='{url}'>{action_text}</a>"
    )

def format_search_result(notifications):
    if not notifications: return "❌ No notices found."
    header = f"🔍 <b>Supreme Search: Found {len(notifications)} Notices</b>\n\n"
    items = []
    for i, n in enumerate(notifications, 1):
        title = n.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        date_str = _format_date(n.published_date)
        icon = get_category_icon(title)
        date_suffix = f" (<i>{date_str}</i>)" if date_str else ""
        items.append(f"{i}. {icon} <a href='{n.source_url}'>{title}</a>{date_suffix}")
    return header + "\n\n".join(items) + "\n\n<i>Supreme system monitoring 24/7.</i>"