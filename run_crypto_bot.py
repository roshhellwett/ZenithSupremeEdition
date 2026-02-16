import os
import asyncio
from fastapi import APIRouter, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from core.logger import setup_logger
from core.config import CRYPTO_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, ADMIN_USER_ID
from zenith_crypto_bot.repository import init_crypto_db, dispose_crypto_engine, SubscriptionRepo
from zenith_crypto_bot.ui import get_main_menu_keyboard, get_welcome_text, get_premium_info_text

logger = setup_logger("SVC_CRYPTO")
router = APIRouter()

bot_app = None
worker_tasks = []
alert_queue = asyncio.Queue() # The Leaky Bucket Queue

# ==========================================
# 👻 1. THE GHOST ADMIN PROTOCOL
# ==========================================
async def cmd_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hidden command to generate subscription keys. Only responds to the Master Admin."""
    if update.effective_user.id != ADMIN_USER_ID:
        return # 🛡️ The "Black Hole": Silent rejection for unauthorized users

    if not context.args:
        return await update.message.reply_text("Admin Format: `/keygen [DAYS]`", parse_mode="Markdown")
        
    try:
        days = int(context.args[0])
        new_key = await SubscriptionRepo.generate_key(days)
        await update.message.reply_text(f"🔑 <b>Zenith Pro {days}-Day Key:</b>\n\n<code>{new_key}</code>", parse_mode="HTML")
    except ValueError:
        pass # Silently ignore bad input

# ==========================================
# 💳 2. MONETIZATION & ACTIVATION
# ==========================================
async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Format: `/activate [YOUR_KEY]`", parse_mode="Markdown")
        
    key_string = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key_string)
    
    await update.message.reply_text(msg, parse_mode="HTML")

# ==========================================
# 🎛️ 3. INTERACTIVE DASHBOARD (UX)
# ==========================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the beautiful onboarding dashboard."""
    text = get_welcome_text(update.effective_user.first_name)
    keyboard = get_main_menu_keyboard()
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")

async def handle_menu_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches all button clicks from the dashboard."""
    query = update.callback_query
    await query.answer() # Tell Telegram we received the click
    
    user_id = update.effective_user.id
    action = query.data
    
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_premium = days_left > 0

    if action == "menu_premium":
        text = get_premium_info_text(days_left)
        await query.message.reply_text(text, parse_mode="HTML")

    elif action == "menu_whale":
        if is_premium:
            await query.message.reply_text("⚡ <b>Pro Stream Active:</b> Listening for zero-latency whale movements...", parse_mode="HTML")
            # TODO: Add user to live premium WebSocket broadcast list
        else:
            await query.message.reply_text("⏳ <b>Free Stream Active:</b> Listening for delayed whale movements...\n<i>(Upgrade to Pro for instant alerts and wallet links)</i>", parse_mode="HTML")

    elif action == "menu_audit":
        await query.message.reply_text("🛡️ <b>Smart Contract Auditor</b>\nReply to this message with a Token Contract Address to scan for Honeypots and hidden mints.", parse_mode="HTML")
        
    elif action == "menu_spikes":
        await query.message.reply_text("📈 <b>DexScreener Radar</b>\nScanning for micro-cap volume spikes in the last 5 minutes...", parse_mode="HTML")

# ==========================================
# 🌊 4. THE LEAKY BUCKET (SRE RATE LIMITER)
# ==========================================
async def alert_dispatcher():
    """Drips messages out to prevent Telegram 429 Bans during Whale Storms."""
    while True:
        try:
            # Get an alert from the queue
            chat_id, text, parse_mode = await alert_queue.get()
            
            try:
                await bot_app.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
            
            alert_queue.task_done()
            # 🛡️ Limit: Max 20 messages per second (0.05s delay)
            await asyncio.sleep(0.05) 
        except asyncio.CancelledError:
            break

async def mock_blockchain_watcher():
    """Background task that watches Alchemy/Helius. (Mocked for now)"""
    while True:
        try:
            await asyncio.sleep(3600) # Replace with actual WebSocket logic
        except asyncio.CancelledError:
            break

# ==========================================
# 🚀 5. MICROSERVICE LIFECYCLE
# ==========================================
async def start_service():
    global bot_app, worker_tasks
    if not CRYPTO_BOT_TOKEN:
        logger.warning("⚠️ CRYPTO_BOT_TOKEN missing! Crypto Service disabled.")
        return

    await init_crypto_db()
    
    # 1. Build Bot & Attach Handlers
    bot_app = ApplicationBuilder().token(CRYPTO_BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("activate", cmd_activate))
    bot_app.add_handler(CommandHandler("keygen", cmd_keygen)) # The Ghost Command
    bot_app.add_handler(CallbackQueryHandler(handle_menu_clicks)) # Button Catcher
    
    await bot_app.initialize()
    await bot_app.start()

    # 2. Register Webhook
    webhook_base = (WEBHOOK_URL or "").strip().rstrip('/')
    if webhook_base and not webhook_base.startswith("http"): webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            await bot_app.bot.set_webhook(
                url=f"{webhook_base}/webhook/crypto/{WEBHOOK_SECRET}",
                secret_token=WEBHOOK_SECRET,
                allowed_updates=Update.ALL_TYPES
            )
            logger.info("✅ Crypto Bot Online & Webhook Registered.")
        except Exception as e:
            logger.error(f"❌ Crypto Bot Webhook Failed: {e}")

    # 3. Start SRE Background Tasks
    worker_tasks.append(asyncio.create_task(alert_dispatcher()))
    worker_tasks.append(asyncio.create_task(mock_blockchain_watcher()))

async def stop_service():
    for task in worker_tasks: task.cancel()
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await dispose_crypto_engine()

# ==========================================
# 🌐 6. FASTAPI WEBHOOK ROUTER
# ==========================================
@router.post("/webhook/crypto/{secret}")
async def crypto_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET: return Response(status_code=403)
    if not bot_app: return Response(status_code=503)
    
    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Crypto Webhook Error: {e}")
        return Response(status_code=500)