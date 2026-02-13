import os
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from group_bot.filters import is_inappropriate
from group_bot.flood_control import is_flooding
from group_bot.violation_tracker import add_strike

logger = logging.getLogger("GROUP_BOT")

async def group_monitor_handler(update: Update, context):
    # Safety: Ignore empty messages or bots
    if not update.message or not update.message.text or update.message.from_user.is_bot: 
        return

    text = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    logger.info(f"🛡️ Scanning message from @{user.username}: {text[:30]}")

    # 1. Forensic Scan for Abuse
    violation, reason = await is_inappropriate(text)
    
    # 2. Flood/Spam Scan
    if not violation: 
        violation, reason = is_flooding(user.id, text)
    
    if violation:
        logger.warning(f"🚨 VIOLATION DETECTED: @{user.username} | Reason: {reason}")
        try:
            # Delete offending message immediately
            await update.message.delete()
            
            # Strike system integration
            await add_strike(user.id)
            
            # Temporary public alert
            alert = await context.bot.send_message(
                chat_id=chat_id, 
                text=f"🛡️ <b>DELETED:</b> @{user.username}, please follow community rules.\nReason: {reason}.",
                parse_mode="HTML"
            )
            
            # Auto-delete alert after 10 seconds
            await asyncio.sleep(10)
            await alert.delete()
            
        except Exception as e: 
            logger.error(f"Moderation Enforcement Error: {e}")

async def start_group_bot():
    token = os.getenv("GROUP_BOT_TOKEN")
    if not token: return

    app = ApplicationBuilder().token(token).build()
    
    # Register the handler for all group text that isn't a command
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & (~filters.COMMAND), group_monitor_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("GROUP HUB ONLINE: ENFORCEMENT ENGINE ACTIVE")
    
    # CRITICAL FIX: Keep this coroutine alive forever so the task doesn't finish
    await asyncio.Event().wait()
    #@academictelebotbyroshhellwett