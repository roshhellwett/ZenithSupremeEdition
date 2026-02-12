import os
import logging
import asyncio
import time
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from group_bot.filters import is_inappropriate
from group_bot.flood_control import is_flooding
from group_bot.violation_tracker import add_strike, MUTE_DURATION_SECONDS
from core.config import ADMIN_ID

logger = logging.getLogger("GROUP_BOT")

WELCOME_COOLDOWN = 30  
last_welcome_time = 0

async def toggle_group_lock(context, chat_id, lock=True):
    """Locks or unlocks the group for maintenance windows."""
    try:
        permissions = ChatPermissions(can_send_messages=not lock)
        await context.bot.set_chat_permissions(chat_id=chat_id, permissions=permissions)
        
        status_text = "⚠️ <b>MAINTENANCE MODE:</b> Group is temporarily locked for system updates." if lock else "✅ <b>ONLINE:</b> Maintenance complete. Group is now active."
        msg = await context.bot.send_message(chat_id=chat_id, text=status_text, parse_mode="HTML")
        
        if not lock:
            async def auto_delete_notice():
                await asyncio.sleep(60)
                try: await msg.delete()
                except: pass
            asyncio.create_task(auto_delete_notice())
    except Exception as e:
        logger.error(f"Group Lock Error: {e}")

async def start_group_bot():
    token = os.getenv("GROUP_BOT_TOKEN")
    if not token:
        logger.error("GROUP_BOT_TOKEN missing!")
        return

    app = ApplicationBuilder().token(token).read_timeout(30).connect_timeout(30).build()

    async def send_welcome_hub(chat_id, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📢 Official Notification Channel", url="https://t.me/teleacademicbot")],
            [InlineKeyboardButton("🔍 Search Past Notices (Search Bot)", url="https://t.me/makautsearchbot")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = (
            "🎓 <b>Academic Group & Rules</b>\n\n"
            "<b>Quick Links:</b>\n"
            "1. Check the <b>Channel</b> for real-time alerts.\n"
            "2. Use the <b>Search Bot</b> to find specific documents.\n\n"
            "⚖️ <b>Group Rules:</b>\n"
            "• No abusive language or personal attacks.\n"
            "• No spamming or unauthorized links.\n"
            "* MAKAUT UNIVERSITY HAS BEEN INTEGRATED *"
        )
        return await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=reply_markup)

    async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        global last_welcome_time
        now = time.time()
        if now - last_welcome_time > WELCOME_COOLDOWN:
            last_welcome_time = now
            welcome_msg = await send_welcome_hub(update.effective_chat.id, context)
            async def auto_delete():
                await asyncio.sleep(20)
                try: await welcome_msg.delete()
                except: pass
            asyncio.create_task(auto_delete())

    async def group_monitor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text: return
        text, user, chat_id = update.message.text, update.effective_user, update.effective_chat.id
        
        violation, reason = await is_inappropriate(text)
        if not violation: violation, reason = is_flooding(user.id, text)

        if violation:
            try:
                await update.message.delete()
                hit_limit = await add_strike(user.id)
                if hit_limit:
                    until_date = int(time.time() + MUTE_DURATION_SECONDS)
                    await context.bot.restrict_chat_member(chat_id=chat_id, user_id=user.id, permissions=ChatPermissions(can_send_messages=False), until_date=until_date)
                    report_msg = await context.bot.send_message(chat_id=ADMIN_ID, text=f"🛡️ <b>SECURITY ALERT</b>\nUser: @{user.username}\nReason: {reason}", parse_mode="HTML")
                    async def clean_report():
                        await asyncio.sleep(3600)
                        try: await report_msg.delete()
                        except: pass
                    asyncio.create_task(clean_report())
                    msg_text = f"🚫 <b>SUPREME MUTE</b>\nUser: @{user.username}\nAction: Restricted for 1 Hour"
                else:
                    msg_text = f"🛡️ <b>MESSAGE DELETED</b>\nUser: @{user.username}\nReason: {reason}"
                warn_msg = await context.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode="HTML")
                await asyncio.sleep(10)
                await warn_msg.delete()
            except Exception as e: logger.error(f"Enforcement Error: {e}")

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler))
    app.add_handler(CommandHandler("help", lambda u, c: send_welcome_hub(u.effective_chat.id, c)))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_monitor_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("GROUP HUB ONLINE")
#@academictelebotbyroshhellwett