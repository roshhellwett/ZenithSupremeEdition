import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from search_bot.handlers import get_latest_results, search_by_keyword

logger = logging.getLogger("SEARCH_BOT")

async def start_search_bot():
    token = os.getenv("SEARCH_BOT_TOKEN")
    if not token:
        logger.error("SEARCH_BOT_TOKEN missing!")
        return

    app = ApplicationBuilder().token(token).build()
    
    async def start_cmd(update, context):
        if update.effective_chat.type == "private":
            await update.message.reply_text("🔍 Send a keyword to search or use /latest.")

    async def latest_cmd(update, context):
        if update.effective_chat.type == "private":
            result_text = get_latest_results() # Corrected function call
            await update.message.reply_text(result_text, parse_mode="HTML", disable_web_page_preview=True)

    async def handle_msg(update, context):
        if update.effective_chat.type == "private":
            query = update.message.text
            result_text = search_by_keyword(query) # Corrected function call
            await update.message.reply_text(result_text, parse_mode="HTML", disable_web_page_preview=True)

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("latest", latest_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("SEARCH BOT READY & POLLING")