import os
import sys
import asyncio
import psutil
import csv
import io
from datetime import datetime
from telegram import Update, constants
from telegram.ext import ContextTypes
from sqlalchemy import select
from core.config import ADMIN_ID
from database.repository import NotificationRepo, SecurityRepo
from database.db import AsyncSessionLocal
from database.models import Notification
from database.security_models import UserStrike

async def update_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Triggers a Soft Restart. 
    On Railway, code updates happen via GitHub Push. 
    This command is for restarting the process if it hangs.
    """
    if update.effective_user.id != ADMIN_ID: return
    
    msg = await update.message.reply_text("🔄 <b>Admin:</b> Initiating System Restart...", parse_mode="HTML")
    await asyncio.sleep(1) # Allow message to send
    
    # Restarts the current python process
    os.execv(sys.executable, [sys.executable] + sys.argv)

async def send_db_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generates CSV Exports of the PostgreSQL Data.
    Replaces the old SQLite file backup logic.
    """
    if update.effective_user.id != ADMIN_ID: return

    await update.message.send_chat_action(action=constants.ChatAction.UPLOAD_DOCUMENT)
    
    try:
        async with AsyncSessionLocal() as db:
            # --- 1. Export Notifications ---
            result = await db.execute(select(Notification))
            notices = result.scalars().all()
            
            # Create In-Memory CSV
            output_notices = io.StringIO()
            writer = csv.writer(output_notices)
            writer.writerow(["ID", "Title", "Date", "Source URL", "Hash"]) # Header
            for n in notices:
                writer.writerow([n.id, n.title, n.published_date, n.source_url, n.content_hash])
            
            output_notices.seek(0)
            
            # Send CSV
            await update.message.reply_document(
                document=io.BytesIO(output_notices.getvalue().encode('utf-8')),
                filename=f"notices_backup_{datetime.now().strftime('%Y%m%d')}.csv",
                caption=f"📊 <b>Notices Export:</b> {len(notices)} records",
                parse_mode="HTML"
            )

            # --- 2. Export Security Strikes ---
            result_sec = await db.execute(select(UserStrike))
            strikes = result_sec.scalars().all()
            
            output_strikes = io.StringIO()
            writer_sec = csv.writer(output_strikes)
            writer_sec.writerow(["User ID", "Strikes", "Last Violation"]) # Header
            for s in strikes:
                writer_sec.writerow([s.user_id, s.strike_count, s.last_violation])
            
            output_strikes.seek(0)

            await update.message.reply_document(
                document=io.BytesIO(output_strikes.getvalue().encode('utf-8')),
                filename=f"security_backup_{datetime.now().strftime('%Y%m%d')}.csv",
                caption=f"🚫 <b>Security Export:</b> {len(strikes)} active records",
                parse_mode="HTML"
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Export Failed: {e}")

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forensic Health Report using Decoupled Repositories."""
    if update.effective_user.id != ADMIN_ID: return
    
    # System Metrics
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    
    # Database Metrics (Via Repositories)
    try:
        total_notices = await NotificationRepo.get_stats()
        active_strikes = await SecurityRepo.get_active_strikes()
        db_status = "✅ ONLINE"
    except Exception:
        total_notices = "N/A"
        active_strikes = "N/A"
        db_status = "❌ CONNECT ERROR"

    status_msg = (
        "<b>🖥️ ZENITH SYSTEM HEALTH (RAILWAY)</b>\n\n"
        f"<b>📊 CPU:</b> {cpu}% | <b>🧠 RAM:</b> {ram}%\n"
        f"<b>📁 DB Notices:</b> {total_notices}\n"
        f"<b>🚫 Security Flags:</b> {active_strikes}\n\n"
        f"<b>Database:</b> {db_status}\n"
        "✅ <b>Pipeline:</b> HEARTBEAT STABLE"
    )
    await update.message.reply_text(status_msg, parse_mode='HTML')
    #@academictelebotbyroshhellwett