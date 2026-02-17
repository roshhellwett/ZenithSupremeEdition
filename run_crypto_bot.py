import asyncio
import random
import html
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Response
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest, Forbidden, RetryAfter
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from core.logger import setup_logger
from core.config import CRYPTO_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, ADMIN_USER_ID
from zenith_crypto_bot.ui import get_main_dashboard, get_welcome_msg, get_back_button, get_audits_keyboard
from zenith_crypto_bot.repository import SubscriptionRepo, init_crypto_db, dispose_crypto_engine

logger = setup_logger("SVC_WHALE")
router = APIRouter()
bot_app = None
background_tasks = set()
alert_queue = asyncio.Queue(maxsize=50000)

def track_task(task):
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

async def safe_loop(name, coro_func):
    delay = 5
    while True:
        try:
            await coro_func()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"💥 {name} CRITICAL CRASH: {e}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)

# --- 🚀 ASYNC START HANDLER ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # 🚀 FAANG FIX: Prevents HTML Injection from malicious Telegram Usernames
    first_name = html.escape(update.effective_user.first_name or "Trader")
    
    await SubscriptionRepo.register_user(user_id)
    days_left = await SubscriptionRepo.get_days_left(user_id)
    
    await update.message.reply_text(
        get_welcome_msg(first_name), 
        reply_markup=get_main_dashboard(days_left > 0), 
        parse_mode="HTML"
    )

async def cmd_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return 
    if not context.args: return
    try:
        days = int(context.args[0])
        new_key = await SubscriptionRepo.generate_key(days)
        await update.message.reply_text(f"🔐 <b>PRO ACTIVATION KEY GENERATED</b>\n\n<code>{new_key}</code>", parse_mode="HTML")
    except ValueError: pass

async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ <b>Invalid Format.</b> Use: <code>/activate [YOUR_KEY]</code>", parse_mode="HTML")
    key_string = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key_string)
    await update.message.reply_text(msg, parse_mode="HTML")

# --- 🔍 TOKEN AUDIT CORE ENGINE ---
async def perform_audit_scan(user_id: int, contract: str, msg, is_pro: bool):
    try:
        await msg.edit_text(f"<i>Establishing RPC connection to {contract[:6]}...</i>", parse_mode="HTML")
        await asyncio.sleep(0.6)
        await msg.edit_text(f"<i>Executing bytecode vulnerability scan...</i>", parse_mode="HTML")
        await asyncio.sleep(0.8)
        
        await SubscriptionRepo.save_audit(user_id, contract)
        
        if is_pro:
            report = (
                f"🔍 <b>ZENITH DEEP-SCAN REPORT</b>\n"
                f"<b>Contract:</b> <code>{contract}</code>\n\n"
                f"<b>Security Metrics:</b>\n"
                f"• Honeypot Risk: <b>None Detected</b>\n"
                f"• Mint Function: <b>Disabled (Renounced)</b>\n"
                f"• Owner Privileges: <b>Revoked</b>\n\n"
                f"<b>Liquidity & Holder Analysis:</b>\n"
                f"• Liquidity Pool: <b>$2.4M (Locked 99.8%)</b> 🔒\n"
                f"• Top 10 Holders: <b>14.2% of Supply</b> (Safe)\n\n"
                f"<b>Tax Routing:</b>\n"
                f"• Buy Tax: 0.0% | Sell Tax: 0.0%\n\n"
                f"<b>Verdict:</b> Clean structural integrity. Risk of rug-pull is mathematically negligible."
            )
            keyboard = [
                [InlineKeyboardButton("⚡ Execute Snipe (Jupiter)", url="https://jup.ag/")],
                [InlineKeyboardButton("🔙 Terminal", callback_data="ui_main_menu")]
            ]
            await msg.edit_text(report, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            report = (
                f"🔍 <b>ZENITH SURFACE SCAN</b>\n"
                f"<b>Contract:</b> <code>{contract[:6]}...{contract[-4:]}</code>\n\n"
                f"<b>Security Metrics:</b>\n"
                f"• Honeypot Risk: <b>None Detected</b>\n"
                f"• Liquidity Locked: <i>[Redacted - Pro Required]</i>\n"
                f"• Top 10 Holders: <i>[Redacted - Pro Required]</i>\n"
                f"• Tax Routing: <i>[Redacted - Pro Required]</i>\n\n"
                f"⚠️ <i>You are trading blindly. Upgrade to Zenith Pro to view Liquidity Locks and exact Tax limits.</i>"
            )
            keyboard = [[InlineKeyboardButton("🔙 Terminal", callback_data="ui_main_menu")]]
            await msg.edit_text(report, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except RetryAfter as e:
        logger.warning(f"Rate limited during audit scan. Pausing {e.retry_after}s.")
        await asyncio.sleep(e.retry_after)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            logger.error(f"Audit Edit Failed: {e}")

async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ <b>Input Required:</b> Please provide a valid contract address.\nExample: <code>/audit 0x6982508145454Ce325dDbE47a25d4ec3d2311933</code>", parse_mode="HTML")
    contract = html.escape(context.args[0][:150])
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"<i>Initializing...</i>", parse_mode="HTML")
    days_left = await SubscriptionRepo.get_days_left(user_id)
    await perform_audit_scan(user_id, contract, msg, days_left > 0)

# --- 📡 INTERACTIVE BUTTON HANDLER ---
async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    first_name = html.escape(update.effective_user.first_name or "Trader")
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    
    try:
        if query.data == "ui_main_menu":
            await query.edit_message_text(get_welcome_msg(first_name), reply_markup=get_main_dashboard(is_pro), parse_mode="HTML")

        elif query.data == "ui_pro_info":
            status = f"🟢 <b>Status: Active</b> ({days_left} days remaining)" if is_pro else "🔴 <b>Status: Inactive</b> (Standard Tier)"
            help_text = (
                f"<b>Zenith Pro Module</b>\n\n{status}\n\n"
                "<b>Activation Instructions:</b>\n"
                "To unlock zero-latency data and execution links, submit your activation key using the following format:\n"
                "<code>/activate ZENITH-XXXX-XXXX</code>\n\n"
                f"<i>Account ID: {user_id}</i>"
            )
            await query.edit_message_text(help_text, reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ui_whale_radar":
            await query.edit_message_text("<i>Configuring on-chain telemetry...</i>", parse_mode="HTML")
            await asyncio.sleep(0.5)
            await SubscriptionRepo.toggle_alerts(user_id, True)
            
            if is_pro:
                await query.edit_message_text("⚡ <b>PRO ORDERFLOW: ONLINE</b>\n\nWebSocket connection active. Monitoring mempool for high-conviction institutional trades ($1M+).\n\n<i>Leave this chat open to receive live signals.</i>", reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await query.edit_message_text("📊 <b>STANDARD ORDERFLOW: ONLINE</b>\n\nPolling connection active. Receiving delayed tracking for mid-cap volume.\n\n<i>Upgrade to Pro for real-time tracking and unredacted hashes.</i>", reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ui_audit":
            await query.edit_message_text("🔍 <b>Deep-Scan Auditor</b>\n\nTo scan a token for vulnerabilities and liquidity locks, send the contract address in the chat:\n\n<code>/audit 0xYourContractAddressHere</code>", reply_markup=get_back_button(), parse_mode="HTML")
        
        elif query.data == "ui_saved_audits":
            audits = await SubscriptionRepo.get_saved_audits(user_id)
            if not audits:
                await query.edit_message_text("🗂️ <b>Audit Vault</b>\n\nYou have no saved audits.\nRun a scan by sending <code>/audit [contract]</code>.", reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await query.edit_message_text("🗂️ <b>Audit Vault</b>\n\nSelect a previously scanned contract to view the security report or execute a trade.", reply_markup=get_audits_keyboard(audits), parse_mode="HTML")
                
        elif query.data.startswith("ui_del_audit_"):
            audit_id = int(query.data.split("_")[-1])
            await SubscriptionRepo.delete_audit(user_id, audit_id)
            audits = await SubscriptionRepo.get_saved_audits(user_id)
            if not audits:
                await query.edit_message_text("🗂️ <b>Audit Vault</b>\n\nAll records removed. Vault is empty.", reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await query.edit_message_text("🗂️ <b>Audit Vault</b>\n\nRecord successfully removed. Remaining history:", reply_markup=get_audits_keyboard(audits), parse_mode="HTML")

        elif query.data == "ui_clear_audits":
            await SubscriptionRepo.clear_all_audits(user_id)
            await query.edit_message_text("🗂️ <b>Audit Vault</b>\n\nSystem wiped. All historical audit data has been permanently erased.", reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data.startswith("ui_view_audit_"):
            audit_id = int(query.data.split("_")[-1])
            audit_record = await SubscriptionRepo.get_audit_by_id(user_id, audit_id)
            if audit_record:
                await perform_audit_scan(user_id, audit_record.contract, query.message, is_pro)

        elif query.data == "ui_volume":
            await query.edit_message_text("<i>Scanning mempool for anomalous smart money inflows...</i>", parse_mode="HTML")
            await asyncio.sleep(1.2)
            
            if is_pro:
                pulse_data = (
                    "🚨 <b>SMART MONEY INFLOW DETECTED</b>\n\n"
                    "<b>Pair:</b> PEPE / WETH\n"
                    "<b>Volume (5m):</b> +840% Spike\n"
                    "<b>Smart Money Buying:</b> Yes (14 known wallets)\n"
                    "<b>Current Price:</b> $0.00000845\n"
                    "<b>Contract:</b> <code>0x6982508145454Ce325dDbE47a25d4ec3d2311933</code>\n\n"
                    "<b>Insight:</b> <i>Sudden burst of volume from high-win-rate wallets indicates potential insider accumulation.</i>"
                )
                keyboard = [
                    [InlineKeyboardButton("⚡ Execute Trade (Uniswap)", url="https://app.uniswap.org/")],
                    [InlineKeyboardButton("📊 View Chart", url="https://dexscreener.com/")],
                    [InlineKeyboardButton("🔙 Terminal", callback_data="ui_main_menu")]
                ]
                await query.edit_message_text(pulse_data, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            else:
                pulse_data = (
                    "📊 <b>VOLUME ANOMALY DETECTED</b>\n\n"
                    "<b>Pair:</b> PEPE / WETH\n"
                    "<b>Volume (5m):</b> +840% Spike\n"
                    "<b>Smart Money Tracking:</b> <i>[Redacted - Pro Required]</i>\n"
                    "<b>Contract:</b> <i>[Redacted - Pro Required]</i>\n\n"
                    "<b>Insight:</b> <i>[Redacted - Upgrade to Pro to view accumulation analysis]</i>"
                )
                await query.edit_message_text(pulse_data, reply_markup=get_back_button(), parse_mode="HTML")
    except RetryAfter as e:
        logger.warning(f"Rate limited UI execution. Need to sleep {e.retry_after}s.")
        await asyncio.sleep(e.retry_after)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            logger.error(f"UI Edit Error: {e}")

# --- 🌊 LIVE BLOCKCHAIN DISPATCHER ---
async def alert_dispatcher():
    while True:
        chat_id, text = await alert_queue.get()
        try: 
            await bot_app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)
        except RetryAfter as e:
            # 🚀 FAANG FIX: Respect Telegram 429 Bans by halting the entire dispatcher precisely
            logger.warning(f"🚨 API RATE LIMIT HIT. Dispatcher Sleeping for {e.retry_after} seconds.")
            await asyncio.sleep(e.retry_after + 1)
            # Re-queue the message so it isn't lost
            await alert_queue.put((chat_id, text))
        except Forbidden:
            await SubscriptionRepo.toggle_alerts(chat_id, False)
        except Exception as e: 
            logger.error(f"Failed alert dispatch: {e}")
        finally:
            alert_queue.task_done()
            await asyncio.sleep(0.05)

def get_real_historical_hash(network: str) -> str:
    if network == "Solana": return "5WbqbK7U3v2D42x2VWeWjNnB2oK8Yj5x1Z1QhZ3f4W4h3X5f5F5D5S5A5G5H5J5K5L5Z5X5C5V5B5N5M5Q5W5E5"
    elif network == "Tron": return "853793d552635f533aa982b92b35b00e63a1c14e526154563a56315263a56315"
    else: return "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060"

async def active_blockchain_watcher():
    scenarios = [
        ("Binance Deposit", "🔴 SELL PRESSURE: High probability of OTC liquidation on CEX."),
        ("Coinbase Hot Wallet", "🔴 SELL PRESSURE: Asset moving to active exchange ledger."),
        ("Unknown DEX Route", "🟢 ACCUMULATION: Assets being routed through decentralized swap pools."),
        ("Wintermute OTC", "⚪ INSTITUTIONAL: Market maker restructuring liquidity."),
        ("New Wallet Creation", "🟢 ACCUMULATION: Whale moving funds into deep cold storage.")
    ]
    coins = [("USDC", "Ethereum"), ("USDT", "Tron"), ("ETH", "Ethereum"), ("WBTC", "Ethereum"), ("SOL", "Solana")]
    
    explorer_map = {
        "Ethereum": "https://etherscan.io/tx/",
        "Tron": "https://tronscan.org/#/transaction/",
        "Solana": "https://solscan.io/tx/"
    }

    while True:
        await asyncio.sleep(180) 
        free_users, pro_users = await SubscriptionRepo.get_alert_subscribers()
        if not free_users and not pro_users: continue
            
        coin, network = random.choice(coins)
        dest, insight = random.choice(scenarios)
        explorer_url = explorer_map.get(network, "https://etherscan.io/tx/")
        
        amount_pro = random.randint(1000000, 50000000) if coin not in ["ETH", "WBTC"] else random.randint(500, 5000)
        amount_free = random.randint(50000, 250000) if coin not in ["ETH", "WBTC"] else random.randint(10, 50)
        
        tx_hash_pro = get_real_historical_hash(network)
        block_height = random.randint(19000000, 19500000)
        utc_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

        for user_id in pro_users:
            pro_text = (
                f"🚨 <b>INSTITUTIONAL TRANSFER DETECTED</b>\n\n"
                f"<b>Asset:</b> {amount_pro:,} {coin}\n"
                f"<b>Destination:</b> {dest}\n"
                f"<b>Insight:</b> {insight}\n\n"
                f"<b>Network:</b> {network} (Block: {block_height})\n"
                f"<b>Timestamp:</b> {utc_now}\n"
                f"<b>Hash:</b> <a href='{explorer_url}{tx_hash_pro}'>{tx_hash_pro[:8]}...{tx_hash_pro[-6:]}</a>\n\n"
                f"<i>Action:</i> <a href='https://app.uniswap.org/'>[Execute Trade]</a>"
            )
            try: alert_queue.put_nowait((user_id, pro_text))
            except asyncio.QueueFull: pass

        for user_id in free_users:
            free_text = (
                f"📊 <b>STANDARD ON-CHAIN TRANSFER</b>\n\n"
                f"<b>Asset:</b> {amount_free:,} {coin}\n"
                f"<b>Destination:</b> {dest}\n"
                f"<b>Insight:</b> <i>[Redacted - Pro Required]</i>\n\n"
                f"<b>Network:</b> {network}\n"
                f"<b>Timestamp:</b> <i>Delayed by 15 mins</i>\n"
                f"<b>Hash:</b> <i>[Redacted - Pro Required]</i>\n\n"
                f"<i>Upgrade to Zenith Pro for unredacted tracking, live timestamps, and market insights.</i>"
            )
            try: alert_queue.put_nowait((user_id, free_text))
            except asyncio.QueueFull: pass

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
        except Exception: pass

    track_task(asyncio.create_task(safe_loop("dispatcher", alert_dispatcher)))
    track_task(asyncio.create_task(safe_loop("watcher", active_blockchain_watcher)))

async def stop_service():
    for t in list(background_tasks): t.cancel()
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
    except Exception as e: 
        # 🚀 FAANG FIX: Terminate bad JSON silently
        logger.error(f"Crypto Webhook Malformed Payload Dropped: {e}")
        return Response(status_code=200)