import os
import logging
from telegram import ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from search_bot.handlers import get_latest_results, search_by_keyword

logger = logging.getLogger("SEARCH_BOT")

# Supreme Fast Filters
FAST_FILTERS = [["/latest", "BCA", "CSE"], ["Exam", "Result", "Form"]]

async def start_search_bot():
    token = os.getenv("SEARCH_BOT_TOKEN")
    if not token: return

    app = ApplicationBuilder().token(token).build()
    reply_markup = ReplyKeyboardMarkup(FAST_FILTERS, resize_keyboard=True)
    
    async def start_cmd(update, context):
        await update.message.reply_text(
            "🔍 <b>Supreme Search Mode</b>\nSend a keyword or use the filters below.",
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    async def latest_cmd(update, context):
        result_text = get_latest_results()
        await update.message.reply_text(result_text, parse_mode="HTML", disable_web_page_preview=True)

    async def handle_msg(update, context):
        query = update.message.text
        result_text = search_by_keyword(query)
        await update.message.reply_text(result_text, parse_mode="HTML", disable_web_page_preview=True)

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("latest", latest_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("SEARCH BOT GOD MODE ACTIVE")