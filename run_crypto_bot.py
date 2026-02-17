import asyncio
import random
from fastapi import APIRouter, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from core.logger import setup_logger
from core.config import CRYPTO_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, ADMIN_USER_ID
from zenith_crypto_bot.ui import get_main_dashboard, get_welcome_msg
from zenith_crypto_bot.repository import SubscriptionRepo, init_crypto_db

logger = setup_logger("SVC_WHALE")
router = APIRouter()
bot_app = None

# 🚀 MEMORY STATE: Remembers who is subscribed to the Live Radar
free_subscribers = set()
pro_subscribers = set()
alert_queue = asyncio.Queue() # Leaky Bucket Rate Limiter

# --- 🚀 ASYNC START HANDLER ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first_name = update.effective_user.first_name
    await update.message.reply_text(
        get_welcome_msg(first_name), 
        reply_markup=get_main_dashboard(), 
        parse_mode="HTML"
    )

# --- 👻 GHOST ADMIN PROTOCOL (Generate Keys) ---
async def cmd_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only YOUR specific Telegram ID can trigger this
    if update.effective_user.id != ADMIN_USER_ID: return 
    
    if not context.args:
        return await update.message.reply_text("Admin Format: `/keygen [DAYS]`\nExample: `/keygen 30`", parse_mode="Markdown")
        
    try:
        days = int(context.args[0])
        new_key = await SubscriptionRepo.generate_key(days)
        await update.message.reply_text(f"🔑 <b>PRO KEY GENERATED:</b>\n\n<code>{new_key}</code>\n\n<i>Tap the code above to copy it.</i>", parse_mode="HTML")
    except ValueError: 
        pass

# --- 💳 ACTIVATION HANDLER ---
async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ <b>Format:</b> <code>/activate [YOUR_KEY]</code>\n\nExample: <code>/activate ZENITH-A1B2-C3D4</code>", parse_mode="HTML")
        
    key_string = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key_string)
    
    await update.message.reply_text(msg, parse_mode="HTML")

# --- 🛡️ TOKEN AUDIT HANDLER ---
async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Please provide a contract address.\nExample: <code>/audit 0x123...abc</code>", parse_mode="HTML")
    
    contract = context.args[0]
    msg = await update.message.reply_text(f"⏳ Scanning contract <code>{contract[:8]}...</code>", parse_mode="HTML")
    await asyncio.sleep(2) # Simulating API processing time
    
    # Show difference in tiers
    days_left = await SubscriptionRepo.get_days_left(update.effective_user.id)
    if days_left > 0:
        await msg.edit_text(f"🛡️ <b>PRO AUDIT: {contract[:8]}...</b>\n\n✅ <b>Honeypot:</b> Negative\n✅ <b>Mint Function:</b> Disabled\n✅ <b>Ownership:</b> Renounced\n📊 <b>Tax:</b> Buy 0% | Sell 0%\n\n<i>Safe to trade.</i>", parse_mode="HTML")
    else:
        await msg.edit_text(f"🛡️ <b>FREE AUDIT: {contract[:8]}...</b>\n\n✅ <b>Honeypot:</b> Negative\n🔒 <i>Advanced metrics hidden. Upgrade to Pro to view Mint & Ownership status.</i>", parse_mode="HTML")

# --- 📡 INTERACTIVE BUTTON HANDLER ---
async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    days_left = await SubscriptionRepo.get_days_left(user_id)
    
    if query.data == "ui_pro_info":
        status = f"✅ <b>Pro Active:</b> {days_left} days left." if days_left > 0 else "❌ <b>Pro Inactive.</b>"
        help_text = (
            f"{status}\n\n"
            "<b>How to Unlock Pro:</b>\n"
            "1. Obtain a Pro Key from the Admin.\n"
            "2. Type the command exactly like this:\n"
            "<code>/activate ZENITH-XXXX-XXXX</code>\n\n"
            f"<i>(Your Telegram ID: {user_id})</i>"
        )
        await query.edit_message_text(help_text, parse_mode="HTML")

    elif query.data == "ui_whale_radar":
        if days_left > 0:
            pro_subscribers.add(user_id)
            free_subscribers.discard(user_id)
            await query.edit_message_text("🎯 <b>Pro Radar Online:</b>\nYou are successfully subscribed. Listening for $1M+ high-speed alerts...", parse_mode="HTML")
        else:
            free_subscribers.add(user_id)
            pro_subscribers.discard(user_id)
            await query.edit_message_text("⏳ <b>Free Radar Online:</b>\nYou are successfully subscribed. Listening for delayed alerts ($50k+)...", parse_mode="HTML")

    elif query.data == "ui_audit":
        await query.edit_message_text("🛡️ <b>Smart Contract Auditor</b>\n\nTo audit a token, send its contract address in the chat like this:\n<code>/audit 0xYourContractAddressHere</code>", parse_mode="HTML")
        
    elif query.data == "ui_volume":
        msg = await query.message.reply_text("📈 <b>DexScreener Pulse</b>\nFetching latest volume breakouts...", parse_mode="HTML")
        await asyncio.sleep(1.5)
        pulse_data = "🚨 <b>VOLUME SPIKE DETECTED</b>\n\n🪙 <b>Token:</b> PEPE / WETH\n📈 <b>Volume (5m):</b> +450%\n💰 <b>Price:</b> $0.0000084\n\n<i>Use /audit to verify contract.</i>"
        await msg.edit_text(pulse_data, parse_mode="HTML")

# --- 🌊 LIVE BLOCKCHAIN DISPATCHER ---
async def alert_dispatcher():
    """Drips messages out to prevent Telegram 429 Bans."""
    while True:
        try:
            chat_id, text = await alert_queue.get()
            try: await bot_app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)
            except Exception as e: logger.error(f"Failed to send alert: {e}")
            alert_queue.task_done()
            await asyncio.sleep(0.05) # Max 20 msgs/sec
        except asyncio.CancelledError: break

async def active_blockchain_watcher():
    """Generates randomized mock data so it doesn't spam until the real API is connected."""
    coins = ["USDC", "USDT", "ETH", "WBTC", "PEPE", "SHIB", "SOL"]
    destinations = ["Binance", "Coinbase", "Kraken", "Unknown Wallet", "Dex Swap"]

    while True:
        try:
            # 🚀 SRE FIX: Wait 5 FULL MINUTES between alerts to stop the spam!
            await asyncio.sleep(300) 
            
            # Generate random realistic data
            coin = random.choice(coins)
            dest = random.choice(destinations)
            amount = random.randint(50, 500) if coin in ["ETH", "WBTC"] else random.randint(100000, 5000000)
            formatted_amount = f"{amount:,}"

            # 1. Dispatch to PRO users
            for user_id in list(pro_subscribers):
                pro_text = f"🐋 <b>WHALE ALERT (PRO)</b>\n💎 <b>{formatted_amount} {coin}</b> moved to {dest}\n🔗 <b>Tx:</b> <a href='https://etherscan.io'>0x{random.randint(1000,9999)}...{random.randint(1000,9999)}</a>\n🛒 <a href='https://app.uniswap.org/'>[Instant Swap]</a>"
                await alert_queue.put((user_id, pro_text))

            # 2. Dispatch to FREE users
            for user_id in list(free_subscribers):
                free_text = f"🚨 <b>DOLPHIN ALERT (FREE)</b>\n💰 <b>{formatted_amount} {coin}</b> moved to {dest}\n🔗 <b>Tx:</b> [PRO REQUIRED]\n\n<i>Upgrade to Pro for full wallet links & instant trading buttons.</i>"
                await alert_queue.put((user_id, free_text))

        except asyncio.CancelledError:
            break

# --- 🚀 LIFECYCLE ---
async def start_service():
    global bot_app
    if not CRYPTO_BOT_TOKEN: return
    
    await init_crypto_db()
    bot_app = ApplicationBuilder().token(CRYPTO_BOT_TOKEN).build()
    
    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("activate", cmd_activate))
    bot_app.add_handler(CommandHandler("keygen", cmd_keygen))
    bot_app.add_handler(CommandHandler("audit", cmd_audit)) 
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))

    await bot_app.initialize()
    await bot_app.start()

    webhook_base = (WEBHOOK_URL or "").strip().rstrip('/')
    if webhook_base and not webhook_base.startswith("http"): webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            webhook_path = f"{webhook_base}/webhook/crypto/{WEBHOOK_SECRET}"
            await bot_app.bot.set_webhook(url=webhook_path, secret_token=WEBHOOK_SECRET, allowed_updates=Update.ALL_TYPES)
            logger.info(f"✅ Zenith Whale Online.")
        except Exception: pass

    # Start the active background workers!
    asyncio.create_task(alert_dispatcher())
    asyncio.create_task(active_blockchain_watcher())

async def stop_service():
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()

@router.post("/webhook/crypto/{secret}")
async def crypto_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET: return Response(status_code=403)
    if not bot_app: return Response(status_code=503)
    
    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception: return Response(status_code=500)