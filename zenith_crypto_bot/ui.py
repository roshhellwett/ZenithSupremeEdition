from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_dashboard(is_pro: bool = False):
    """The high-tech dashboard for all users."""
    status_text = "💎 Zenith Pro Status" if is_pro else "🔓 Unlock Pro Access"
    radar_text = "⚡ Live Pro Radar" if is_pro else "📡 Live Free Radar"
    
    keyboard = [
        [InlineKeyboardButton(radar_text, callback_data="ui_whale_radar")],
        [InlineKeyboardButton("🛡️ Smart Contract Audit", callback_data="ui_audit")],
        [InlineKeyboardButton("📈 DexScreener Pulse", callback_data="ui_volume")],
        [InlineKeyboardButton(status_text, callback_data="ui_pro_info")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_welcome_msg(name: str):
    return (
        f"🌌 <b>Welcome to Zenith Whale, {name}.</b>\n\n"
        "I am an institutional-grade blockchain intelligence terminal. I monitor the mempool and on-chain liquidity 24/7 to provide you with an asymmetric market edge.\n\n"
        "<b>🟢 FREE TIER CAPABILITIES:</b>\n"
        "• <b>Dolphin Alerts:</b> Delayed tracking of mid-tier transfers ($50k+).\n"
        "• <b>Masked Routing:</b> Transaction flow is visible, but wallet addresses are obfuscated.\n"
        "• <b>Surface Audit:</b> Basic contract security checks.\n\n"
        "<b>💎 ZENITH PRO CAPABILITIES:</b>\n"
        "• <b>Whale Alerts:</b> Zero-latency, real-time push notifications for $1M+ movements.\n"
        "• <b>Unmasked Wallets:</b> Direct Etherscan/Solscan tracking links.\n"
        "• <b>One-Click Trading:</b> Instant DEX swap execution links.\n"
        "• <b>Deep-Scan Audits:</b> Unlimited honeypot, mint, and tax analysis.\n\n"
        "<i>Initialize a module below to begin operations.</i>"
    )