import asyncio
import time
from functools import wraps
from fastapi import APIRouter, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from core.logger import setup_logger
from core.config import ADMIN_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, ADMIN_USER_ID
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_admin_bot.repository import (
    init_admin_db, AdminRepo, BotRegistryRepo, MonitoringRepo, dispose_admin_engine,
)
from zenith_admin_bot.ui import (
    get_admin_main_menu, get_back_button, get_admin_dashboard,
    format_system_overview, format_key_management, format_user_management,
    format_bot_health, format_audit_log, format_revenue_analytics,
    format_subscription_list,
)
from zenith_admin_bot.monitoring import start_monitoring, stop_monitoring

logger = setup_logger("ADMIN")
router = APIRouter()
bot_app = None
background_tasks = set()

_admin_command_timestamps = {}


def track_task(task):
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


def rate_limit_admin(seconds: int = 10):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            command = func.__name__
            key = f"{user_id}:{command}"
            now = time.time()
            
            if key in _admin_command_timestamps:
                last_time = _admin_command_timestamps[key]
                if now - last_time < seconds:
                    if update.message:
                        await update.message.reply_text(
                            f"⏳ Please wait {seconds} seconds between {command} commands."
                        )
                    return
            
            _admin_command_timestamps[key] = now
            return await func(update, context)
        return wrapper
    return decorator


def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_USER_ID:
            if update.message:
                await update.message.reply_text("⛔ Unauthorized.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Unauthorized.", show_alert=True)
            return
        return await func(update, context)
    return wrapper


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        get_admin_dashboard(),
        reply_markup=get_admin_main_menu(),
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(context.args[0]) if context.args else 30
    except ValueError:
        await update.message.reply_text(
            "⚠️ Invalid day count. Usage: <code>/keygen [DAYS]</code>",
            parse_mode="HTML",
        )
        return

    key = await SubscriptionRepo.generate_key(days)
    await AdminRepo.log_action(
        ADMIN_USER_ID, "keygen", details=f"Generated key for {days} days: {key}"
    )
    await update.message.reply_text(
        f"🔑 <b>Key Generated</b>\n\n"
        f"<b>Key:</b> <code>{key}</code>\n"
        f"<b>Duration:</b> {days} days",
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=30)
async def cmd_extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/extend [USER_ID] [DAYS]</code>\n"
            "Example: <code>/extend 123456789 30</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")
        return

    days = 30
    if len(context.args) > 1:
        try:
            days = int(context.args[1])
        except ValueError:
            await update.message.reply_text("⚠️ Invalid day count.")
            return

    success, msg = await SubscriptionRepo.extend_subscription(target_user_id, days)
    await AdminRepo.log_action(
        ADMIN_USER_ID, "extend", target_user_id=target_user_id,
        details=f"Extended by {days} days"
    )

    if success:
        try:
            await bot_app.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"💎 <b>PRO SUBSCRIPTION EXTENDED</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"✅ <b>{days} days</b> have been added to your account.\n"
                    f"Enjoy uninterrupted access to all Pro features!\n\n"
                    f"<i>Type /start to open your terminal.</i>"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

    await update.message.reply_text(msg, parse_mode="HTML")


@admin_only
@rate_limit_admin(seconds=30)
async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/revoke [USER_ID]</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")
        return

    from datetime import datetime, timedelta, timezone
    success, msg = await SubscriptionRepo.extend_subscription(target_user_id, -9999)
    await AdminRepo.log_action(
        ADMIN_USER_ID, "revoke", target_user_id=target_user_id,
        details="Revoked subscription"
    )

    if success:
        try:
            await bot_app.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"❌ <b>SUBSCRIPTION REVOKED</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Your Pro subscription has been revoked.\n"
                    f"Contact admin for details."
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

    await update.message.reply_text(msg, parse_mode="HTML")


@admin_only
async def cmd_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/lookup [USER_ID]</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")
        return

    sub_details = await MonitoringRepo.get_user_subscription_details(target_user_id)
    await AdminRepo.log_action(
        ADMIN_USER_ID, "user_lookup", target_user_id=target_user_id,
        details="Looked up user subscription"
    )

    await update.message.reply_text(
        format_user_management(target_user_id, sub_details),
        parse_mode="HTML",
    )


@admin_only
async def cmd_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = await MonitoringRepo.get_recent_keys(limit=10)
    await update.message.reply_text(
        format_key_management(keys),
        parse_mode="HTML",
    )


@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await MonitoringRepo.get_subscription_stats()
    ticket_stats = await MonitoringRepo.get_ticket_stats()

    await update.message.reply_text(
        format_system_overview(stats, ticket_stats),
        parse_mode="HTML",
    )


@admin_only
async def cmd_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscriptions = await MonitoringRepo.get_all_active_subscriptions()
    await update.message.reply_text(
        format_subscription_list(subscriptions),
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=60)
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/broadcast [MESSAGE]</code>",
            parse_mode="HTML",
        )
        return

    message = " ".join(context.args)
    await update.message.reply_text(
        f"📢 <b>Broadcast to all users</b>\n\n"
        f"<i>Note: Broadcasting not yet implemented.</i>\n\n"
        f"<b>Message:</b> {message}",
        parse_mode="HTML",
    )
    await AdminRepo.log_action(
        ADMIN_USER_ID, "broadcast", details=f"Broadcast: {message[:100]}"
    )


@admin_only
async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logs = await AdminRepo.get_audit_trail(limit=20)
    await update.message.reply_text(
        format_audit_log(logs),
        parse_mode="HTML",
    )


@admin_only
async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bots = await BotRegistryRepo.get_all_bots()
    await update.message.reply_text(
        format_bot_health(bots),
        parse_mode="HTML",
    )


@admin_only
async def cmd_botlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bots = await BotRegistryRepo.get_all_bots()
    await update.message.reply_text(
        format_bot_health(bots),
        parse_mode="HTML",
    )


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        await query.answer("⛔ Unauthorized.", show_alert=True)
        return

    try:
        if query.data == "admin_main":
            await query.edit_message_text(
                get_admin_dashboard(),
                reply_markup=get_admin_main_menu(),
                parse_mode="HTML",
            )

        elif query.data == "admin_overview":
            stats = await MonitoringRepo.get_subscription_stats()
            ticket_stats = await MonitoringRepo.get_ticket_stats()
            await query.edit_message_text(
                format_system_overview(stats, ticket_stats),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_keys":
            keys = await MonitoringRepo.get_recent_keys(limit=10)
            await query.edit_message_text(
                format_key_management(keys),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_users":
            await query.edit_message_text(
                "<b>👤 USER MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Use commands:\n"
                "• <code>/lookup [USER_ID]</code> — View user subscription\n"
                "• <code>/extend [USER_ID] [DAYS]</code> — Extend subscription\n"
                "• <code>/revoke [USER_ID]</code> — Revoke subscription",
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_health":
            bots = await BotRegistryRepo.get_all_bots()
            await query.edit_message_text(
                format_bot_health(bots),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_audit":
            logs = await AdminRepo.get_audit_trail(limit=20)
            await query.edit_message_text(
                format_audit_log(logs),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_revenue":
            stats = await MonitoringRepo.get_subscription_stats()
            await query.edit_message_text(
                format_revenue_analytics(stats),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_back":
            await query.edit_message_text(
                get_admin_dashboard(),
                reply_markup=get_admin_main_menu(),
                parse_mode="HTML",
            )

    except Exception as e:
        if "not modified" not in str(e).lower():
            logger.error(f"Dashboard callback error: {e}")


async def start_service():
    global bot_app
    if not ADMIN_BOT_TOKEN:
        logger.warning("⚠️ ADMIN_BOT_TOKEN missing! Admin Service disabled.")
        return

    await init_admin_db()
    bot_app = ApplicationBuilder().token(ADMIN_BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("keygen", cmd_keygen))
    bot_app.add_handler(CommandHandler("extend", cmd_extend))
    bot_app.add_handler(CommandHandler("revoke", cmd_revoke))
    bot_app.add_handler(CommandHandler("lookup", cmd_lookup))
    bot_app.add_handler(CommandHandler("keys", cmd_keys))
    bot_app.add_handler(CommandHandler("stats", cmd_stats))
    bot_app.add_handler(CommandHandler("subs", cmd_subs))
    bot_app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    bot_app.add_handler(CommandHandler("audit", cmd_audit))
    bot_app.add_handler(CommandHandler("health", cmd_health))
    bot_app.add_handler(CommandHandler("botlist", cmd_botlist))
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))

    await bot_app.initialize()
    await bot_app.start()

    webhook_base = (WEBHOOK_URL or "").strip().rstrip("/")
    if webhook_base and not webhook_base.startswith("http"):
        webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            await bot_app.bot.set_webhook(
                url=f"{webhook_base}/webhook/admin/{WEBHOOK_SECRET}",
                secret_token=WEBHOOK_SECRET,
                allowed_updates=Update.ALL_TYPES,
            )
            logger.info("✅ Admin Bot Online & Webhook Registered.")
        except Exception as e:
            logger.error(f"❌ Admin Bot Webhook Failed: {e}")

    await start_monitoring(bot_app)
    logger.info("👑 Admin Bot: Online")


async def stop_service():
    await stop_monitoring()

    for t in list(background_tasks):
        t.cancel()

    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()

    await dispose_admin_engine()
    logger.info("👑 Admin Bot: Stopped")


@router.post("/webhook/admin/{secret}")
async def admin_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return Response(status_code=403)
    if not bot_app:
        return Response(status_code=503)

    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Admin Webhook Error: {e}")
        return Response(status_code=200)
