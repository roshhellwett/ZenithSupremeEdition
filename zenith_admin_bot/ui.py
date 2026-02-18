from datetime import datetime
from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_admin_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📊 System Overview", callback_data="admin_overview")],
        [InlineKeyboardButton("🔑 Key Management", callback_data="admin_keys")],
        [InlineKeyboardButton("👤 User Management", callback_data="admin_users")],
        [InlineKeyboardButton("🤖 Bot Health", callback_data="admin_health")],
        [InlineKeyboardButton("📋 Audit Log", callback_data="admin_audit")],
        [InlineKeyboardButton("📈 Revenue Analytics", callback_data="admin_revenue")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_main")]])


def get_admin_dashboard() -> str:
    return (
        "<b>🎛️ ZENITH ADMIN PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Welcome to the central admin dashboard.\n"
        "Select an option below to manage your bots."
    )


def format_system_overview(stats: dict, ticket_stats: dict) -> str:
    lines = [
        "<b>📊 SYSTEM OVERVIEW</b>\n━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"<b>👥 Total Users:</b> {stats.get('total_users', 0):,}",
        f"<b>💎 Pro Users:</b> {stats.get('pro_users', 0):,}",
        f"<b>🆓 Free Users:</b> {stats.get('free_users', 0):,}",
        "",
        f"<b>📜 Active Subscriptions:</b> {stats.get('active_subscriptions', 0):,}",
        f"<b>⚠️ Expiring (7 days):</b> {stats.get('expiring_within_7_days', 0):,}",
        "",
        "<b>🎫 SUPPORT TICKETS</b>",
        f"<b>Total:</b> {ticket_stats.get('total', 0)}",
        f"<b>Open:</b> {ticket_stats.get('open', 0)}",
        f"<b>In Progress:</b> {ticket_stats.get('in_progress', 0)}",
        f"<b>Resolved:</b> {ticket_stats.get('resolved', 0)}",
    ]
    return "\n".join(lines)


def format_key_management(keys: List) -> str:
    if not keys:
        return "<b>🔑 KEY MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nNo unused activation keys found."

    lines = ["<b>🔑 UNUSED ACTIVATION KEYS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━"]
    for key in keys:
        days = key.duration_days
        created = key.created_at.strftime("%d %b %Y") if key.created_at else "N/A"
        lines.append(f"• <code>{key.key_string}</code> ({days}d) - {created}")

    return "\n".join(lines)


def format_user_management(user_id: int, sub_details: dict) -> str:
    if not sub_details.get("has_subscription", False):
        return (
            f"<b>👤 USER: {user_id}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Subscription:</b> ❌ None\n"
            f"<b>Status:</b> Free tier"
        )

    expires = sub_details.get("expires_at")
    expires_str = expires.strftime("%d %b %Y") if expires else "N/A"

    return (
        f"<b>👤 USER: {user_id}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Subscription:</b> ✅ Active\n"
        f"<b>Days Remaining:</b> {sub_details.get('days_left', 0)}\n"
        f"<b>Expires:</b> {expires_str}"
    )


def format_bot_health(bots: List) -> str:
    if not bots:
        return "<b>🤖 BOT HEALTH</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nNo bots registered."

    lines = ["<b>🤖 MONITORED BOTS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━"]
    for bot in bots:
        status_icon = "🟢" if bot.status == "active" else ("🔴" if bot.status == "error" else "🟡")
        health = bot.health_status or "unknown"
        last_check = bot.last_health_check.strftime("%d %b %H:%M") if bot.last_health_check else "Never"
        lines.append(f"{status_icon} <b>{bot.bot_name}</b>\n   Status: {bot.status} | Health: {health}\n   Last check: {last_check}")

    return "\n".join(lines)


def format_audit_log(logs: List) -> str:
    if not logs:
        return "<b>📋 AUDIT LOG</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nNo recent admin actions."

    lines = ["<b>📋 RECENT ADMIN ACTIONS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━"]
    for log in logs[:15]:
        action_icon = {
            "keygen": "🔑",
            "extend": "⏰",
            "revoke": "❌",
            "broadcast": "📢",
            "user_lookup": "👤",
            "bot_register": "🤖",
            "bot_unregister": "🛑",
        }.get(log.action.value, "•")

        time_str = log.created_at.strftime("%d %b %H:%M") if log.created_at else "N/A"
        target = f"User: {log.target_user_id}" if log.target_user_id else ""
        details = f" - {log.details}" if log.details else ""

        lines.append(
            f"{action_icon} <b>{log.action.value.upper()}</b> {time_str}\n"
            f"   {target}{details}"
        )

    return "\n".join(lines)


def format_revenue_analytics(stats: dict) -> str:
    pro_users = stats.get("pro_users", 0)
    active_subs = stats.get("active_subscriptions", 0)
    avg_value_per_user = 9.99
    estimated_mrr = active_subs * avg_value_per_user

    lines = [
        "<b>📈 REVENUE ANALYTICS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"<b>💎 Pro Users:</b> {pro_users:,}",
        f"<b>📜 Active Subs:</b> {active_subs:,}",
        f"<b>⚠️ At Risk (7d):</b> {stats.get('expiring_within_7_days', 0):,}",
        "",
        "<b>💰 ESTIMATED MRR</b>",
        f"<b>Active Subs × $9.99:</b> ${estimated_mrr:,.2f}",
        "",
        "<i>Note: Based on $9.99/month base plan</i>",
    ]
    return "\n".join(lines)


def format_subscription_list(subscriptions: List) -> str:
    if not subscriptions:
        return "<b>📜 ACTIVE SUBSCRIPTIONS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\nNo active subscriptions."

    lines = ["<b>📜 ACTIVE SUBSCRIPTIONS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━"]
    for sub in subscriptions[:20]:
        expires = sub.expires_at.strftime("%d %b %Y") if sub.expires_at else "N/A"
        days_left = (sub.expires_at - datetime.now()).days if sub.expires_at else 0
        lines.append(f"• <code>{sub.user_id}</code> - {expires} ({days_left}d)")

    if len(subscriptions) > 20:
        lines.append(f"\n<i>...and {len(subscriptions) - 20} more</i>")

    return "\n".join(lines)


def get_user_management_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔍 Lookup User", callback_data="admin_user_lookup")],
        [InlineKeyboardButton("➕ Extend Subscription", callback_data="admin_user_extend")],
        [InlineKeyboardButton("❌ Revoke Subscription", callback_data="admin_user_revoke")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_key_management_keyboard() -> InlineKeyboardButton:
    keyboard = [
        [InlineKeyboardButton("🔑 Generate Key", callback_data="admin_keygen")],
        [InlineKeyboardButton("📋 List Keys", callback_data="admin_keys_list")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(keyboard)
