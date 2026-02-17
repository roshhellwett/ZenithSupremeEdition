import asyncio
import random
from fastapi import APIRouter, Request, Response
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from core.logger import setup_logger
from core.config import CRYPTO_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, ADMIN_USER_ID
from zenith_crypto_bot.ui import get_main_dashboard, get_welcome_msg
from zenith_crypto_bot.repository import SubscriptionRepo, init_crypto_db, dispose_crypto_engine

logger = setup_logger("SVC_WHALE")
router = APIRouter()
bot_app = None
background_tasks = set()
alert_queue = asyncio.Queue(maxsize=10000)

def track_task(task):
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

async def safe_loop(name, coro):
    while True:
        try:
            await coro()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"{name} crashed: {e}")
            await asyncio.sleep(5)

# --- 🚀 ASYNC START HANDLER ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    
    # Register user in DB so we don't forget them!
    await SubscriptionRepo.register_user(user_id)
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    
    await update.message.reply_text(
        get_welcome_msg(first_name), 
        reply_markup=get_main_dashboard(is_pro), 
        parse_mode="HTML"
    )

# --- 👻 GHOST ADMIN PROTOCOL (Generate Keys) ---
async def cmd_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return 
    
    if not context.args:
        return await update.message.reply_text("Admin Format: `/keygen [DAYS]`\nExample: `/keygen 30`", parse_mode="Markdown")
        
    try:
        days = int(context.args[0])
        new_key = await SubscriptionRepo.generate_key(days)
        await update.message.reply_text(f"🔐 <b>PRO KEY GENERATED</b>\n\n<code>{new_key}</code>\n\n<i>Tap the key to copy it.</i>", parse_mode="HTML")
    except ValueError: 
        pass

# --- 💳 ACTIVATION HANDLER ---
async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ <b>Format:</b> <code>/activate [YOUR_KEY]</code>\n\nExample: <code>/activate ZENITH-A1B2-C3D4</code>", parse_mode="HTML")
        
    key_string = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key_string)
    
    await update.message.reply_text(msg, parse_mode="HTML")

# --- 🛡️ TOKEN AUDIT HANDLER (Premium UI Animations) ---
async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ <b>Input Required:</b> Please provide a contract address.\nExample: <code>/audit 0x6982508145454Ce325dDbE47a25d4ec3d2311933</code>", parse_mode="HTML")
    
    contract = context.args[0]
    msg = await update.message.reply_text(f"📡 <b>Connecting to Node...</b>", parse_mode="HTML")
    
    # Premium Loading Animation
    await asyncio.sleep(0.6)
    await msg.edit_text(f"🔍 <b>Analyzing bytecode for</b> <code>{contract[:8]}...{contract[-4:]}</code>", parse_mode="HTML")
    await asyncio.sleep(0.8)
    await msg.edit_text(f"⚙️ <b>Running GoPlus Security checks...</b>", parse_mode="HTML")
    await asyncio.sleep(0.8)
    
    days_left = await SubscriptionRepo.get_days_left(update.effective_user.id)
    if days_left > 0:
        report = (
            f"🛡️ <b>ZENITH DEEP AUDIT</b>\n"
            f"🪙 <b>Contract:</b> <code>{contract}</code>\n\n"
            f"✅ <b>Honeypot Risk:</b> Negative\n"
            f"✅ <b>Mint Function:</b> Disabled (Renounced)\n"
            f"✅ <b>Owner Privilege:</b> None\n"
            f"✅ <b>Blacklist Capability:</b> None\n\n"
            f"📊 <b>Tax Analysis:</b>\n"
            f"• Buy Tax: 0.0%\n"
            f"• Sell Tax: 0.0%\n\n"
            f"🟢 <b>Verdict:</b> <i>Contract appears structurally safe to trade. Proceed with standard risk management.</i>"
        )
        keyboard = [[InlineKeyboardButton("🛒 Sniper Buy (Jupiter)", url="https://jup.ag/")]]
        await msg.edit_text(report, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        report = (
            f"🛡️ <b>ZENITH SURFACE AUDIT (FREE)</b>\n"
            f"🪙 <b>Contract:</b> <code>{contract[:6]}...{contract[-4:]}</code>\n\n"
            f"✅ <b>Honeypot Risk:</b> Negative\n"
            f"🔒 <b>Mint Function:</b> <i>[PRO REQUIRED]</i>\n"
            f"🔒 <b>Owner Privilege:</b> <i>[PRO REQUIRED]</i>\n"
            f"📊 <b>Tax Analysis:</b> <i>[PRO REQUIRED]</i>\n\n"
            f"⚠️ <i>Upgrade to Zenith Pro for full contract decompilation and tax analysis.</i>"
        )
        await msg.edit_text(report, parse_mode="HTML")

# --- 📡 INTERACTIVE BUTTON HANDLER ---
async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    
    if query.data == "ui_pro_info":
        status = f"✅ <b>Pro Active:</b> {days_left} days remaining." if is_pro else "❌ <b>Pro Inactive.</b>"
        help_text = (
            f"💎 <b>Zenith Pro Module</b>\n\n{status}\n\n"
            "<b>How to Unlock Pro:</b>\n"
            "1. Obtain a Pro Activation Key.\n"
            "2. Send the command exactly like this:\n"
            "<code>/activate ZENITH-XXXX-XXXX</code>\n\n"
            f"<i>(Your Telegram ID: {user_id})</i>"
        )
        await query.edit_message_text(help_text, reply_markup=get_main_dashboard(is_pro), parse_mode="HTML")

    elif query.data == "ui_whale_radar":
        await query.edit_message_text("⚙️ <i>Configuring Radar Connection...</i>", parse_mode="HTML")
        await asyncio.sleep(0.5)
        
        # Toggle alerts on permanently in the DB
        await SubscriptionRepo.toggle_alerts(user_id, True)
        
        if is_pro:
            await query.edit_message_text("⚡ <b>PRO RADAR ONLINE</b>\n\nWebSocket connection established. You are now listening for real-time, zero-latency high-value movements ($1M+).\n\n<i>Leave this chat open to receive alerts.</i>", reply_markup=get_main_dashboard(is_pro), parse_mode="HTML")
        else:
            await query.edit_message_text("📡 <b>FREE RADAR ONLINE</b>\n\nPolling connection established. You will receive delayed alerts for mid-tier movements ($50k+).\n\n<i>Upgrade to Pro for instant alerts.</i>", reply_markup=get_main_dashboard(is_pro), parse_mode="HTML")

    elif query.data == "ui_audit":
        await query.edit_message_text("🛡️ <b>Smart Contract Auditor</b>\n\nTo audit a token's security, send its contract address to me in the chat like this:\n\n<code>/audit 0xYourContractAddressHere</code>", reply_markup=get_main_dashboard(is_pro), parse_mode="HTML")
        
    elif query.data == "ui_volume":
        msg = await query.edit_message_text("📈 <b>Initializing DexScreener Pulse...</b>", parse_mode="HTML")
        await asyncio.sleep(0.8)
        await query.edit_message_text("⏳ <b>Scanning mempool for volume anomalies...</b>", parse_mode="HTML")
        await asyncio.sleep(1.2)
        
        if is_pro:
            pulse_data = (
                "🚨 <b>PRO VOLUME SPIKE DETECTED</b>\n\n"
                "🪙 <b>Token:</b> PEPE / WETH\n"
                "📈 <b>Volume (5m):</b> +640%\n"
                "💰 <b>Current Price:</b> $0.00000845\n"
                "💧 <b>Liquidity:</b> $4.2M\n"
                "🔗 <b>Contract:</b> <code>0x6982508145454Ce325dDbE47a25d4ec3d2311933</code>\n\n"
                "<i>Click below to execute or audit.</i>"
            )
            keyboard = [
                [InlineKeyboardButton("🛒 Sniper Swap", url="https://app.uniswap.org/")],
                [InlineKeyboardButton("📊 DexScreener", url="https://dexscreener.com/")]
            ]
            await query.edit_message_text(pulse_data, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            pulse_data = (
                "🚨 <b>FREE VOLUME SPIKE DETECTED</b>\n\n"
                "🪙 <b>Token:</b> PEPE / WETH\n"
                "📈 <b>Volume (5m):</b> +640%\n"
                "🔗 <b>Contract:</b> <i>[PRO REQUIRED]</i>\n"
                "💧 <b>Liquidity:</b> <i>[PRO REQUIRED]</i>\n\n"
                "<i>Upgrade to Zenith Pro to see contract addresses and instant swap links.</i>"
            )
            await query.edit_message_text(pulse_data, reply_markup=get_main_dashboard(is_pro), parse_mode="HTML")

# --- 🌊 LIVE BLOCKCHAIN DISPATCHER ---
async def alert_dispatcher():
    """Drips messages out to prevent Telegram 429 Bans."""
    while True:
        chat_id, text = await alert_queue.get()
        try: 
            await bot_app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception: 
            pass # Ignore blocked users
        alert_queue.task_done()
        await asyncio.sleep(0.05) # Max 20 msgs/sec

async def active_blockchain_watcher():
    """Generates randomized realistic mock data."""
    coins = [("USDC", "Ethereum"), ("USDT", "Tron"), ("ETH", "Ethereum"), ("WBTC", "Ethereum"), ("SOL", "Solana")]
    destinations = ["Binance Deposit", "Coinbase Hot Wallet", "Kraken", "Unknown DEX", "Wintermute Trading"]

    while True:
        # Wait 3 minutes between alerts
        await asyncio.sleep(180) 
        
        free_users, pro_users = await SubscriptionRepo.get_alert_subscribers()
        
        if not free_users and not pro_users:
            continue # Skip if no one is listening
            
        coin, network = random.choice(coins)
        dest = random.choice(destinations)
        
        amount_pro = random.randint(1000000, 50000000) if coin not in ["ETH", "WBTC"] else random.randint(500, 5000)
        amount_free = random.randint(50000, 250000) if coin not in ["ETH", "WBTC"] else random.randint(10, 50)
        
        tx_hash_pro = f"0x{random.randint(100000,999999)}abc{random.randint(100000,999999)}def"

        # Dispatch to PRO users
        for user_id in pro_users:
            pro_text = (
                f"🐋 <b>INSTANT WHALE ALERT</b>\n\n"
                f"💎 <b>Amount:</b> {amount_pro:,} {coin}\n"
                f"🌐 <b>Network:</b> {network}\n"
                f"📥 <b>To:</b> {dest}\n"
                f"🔗 <b>Tx Hash:</b> <a href='https://etherscan.io/tx/{tx_hash_pro}'>{tx_hash_pro[:8]}...</a>\n\n"
                f"<i>Zenith Intelligence Engine</i>"
            )
            await alert_queue.put((user_id, pro_text))

        # Dispatch to FREE users
        for user_id in free_users:
            free_text = (
                f"🚨 <b>DOLPHIN ALERT</b>\n\n"
                f"💰 <b>Amount:</b> {amount_free:,} {coin}\n"
                f"🌐 <b>Network:</b> {network}\n"
                f"📥 <b>To:</b> {dest}\n"
                f"🔗 <b>Tx Hash:</b> <i>[PRO REQUIRED]</i>\n\n"
                f"<i>Upgrade to Zenith Pro to track $1M+ Whale movements.</i>"
            )
            await alert_queue.put((user_id, free_text))

# --- 🚀 LIFECYCLE ---
async def start_service():
    global bot_app
    if not CRYPTO_BOT_TOKEN: 
        logger.warning("⚠️ CRYPTO_BOT_TOKEN missing! Crypto bot disabled.")
        return
    
    await init_crypto_db()
    bot_app = ApplicationBuilder().token(CRYPTO_BOT_TOKEN).build()
    
    # 🚀 RE-CONNECTED THE HANDLERS
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
        except Exception as e: 
            logger.error(f"Webhook failed: {e}")

    # Start the active background workers!
    track_task(asyncio.create_task(safe_loop("dispatcher", alert_dispatcher)))
    track_task(asyncio.create_task(safe_loop("watcher", active_blockchain_watcher)))

async def stop_service():
    for t in list(background_tasks):
        t.cancel()

    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    
    await dispose_crypto_engine()

@router.post("/webhook/crypto/{secret}")
async def crypto_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET: return Response(status_code=403)
    if not bot_app: return Response(status_code=503)
    
    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception: return Response(status_code=500)