from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard():
    """Generates the main interactive dashboard."""
    keyboard = [
        [InlineKeyboardButton("🐋 Live Whale Stream", callback_data="menu_whale")],
        [InlineKeyboardButton("🛡️ Audit Token", callback_data="menu_audit"),
         InlineKeyboardButton("📈 Volume Spikes", callback_data="menu_spikes")],
        [InlineKeyboardButton("💎 Premium Access / Status", callback_data="menu_premium")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_welcome_text(first_name: str) -> str:
    """The master onboarding text."""
    return (
        f"👋 Welcome to <b>Zenith Whale</b>, {first_name}.\n\n"
        "I am an institutional-grade crypto intelligence terminal. I monitor the blockchain 24/7 to track "
        "smart money, audit malicious contracts, and spot market breakouts before they happen.\n\n"
        "<b>📊 FREE TIER CAPABILITIES:</b>\n"
        "• Delayed Whale Alerts (5-10 min lag)\n"
        "• Basic Contract Auditing (3 per day)\n"
        "• Masked Wallet Addresses\n\n"
        "<b>💎 ZENITH PRO CAPABILITIES:</b>\n"
        "• ⚡ Zero-Latency Instant Alerts\n"
        "• 🔗 Uncensored Wallet Tracking Links\n"
        "• 🛒 Direct 1-Click Swap Buttons (DEX)\n"
        "• 🛡️ Unlimited Deep-Scan Audits\n\n"
        "<i>Select a module below to begin:</i>"
    )

def get_premium_info_text(days_left: int = 0) -> str:
    """Status screen for the user."""
    if days_left > 0:
        return f"💎 <b>Zenith Pro Active</b>\nYou have <b>{days_left} days</b> of premium access remaining. You are receiving real-time, zero-latency data."
    else:
        return (
            "🚫 <b>No Active Subscription</b>\n\n"
            "You are currently on the Free Tier. To unlock real-time alerts and direct trading links, "
            "you must purchase an activation key.\n\n"
            "<b>How to activate:</b>\n"
            "If you have a key, send this command:\n"
            "<code>/activate [YOUR_KEY]</code>"
        )