import os
import sys
import asyncio
import psutil
from sqlalchemy import func, select
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_ID, CHANNEL_ID
from database.db import AsyncSessionLocal
from database.models import Notification, UserStrike

# Global state for maintenance mode
is_maintenance = False

async def maintenance_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Suspends services for X minutes to allow local testing."""
    if update.effective_user.id != ADMIN_ID: 
        return
    global is_maintenance
    
    try:
        duration_mins = int(context.args[0]) if context.args else 1
        await update.message.reply_text(f"🚧 <b>Maintenance:</b> Suspending for {duration_mins}m.")
        
        is_maintenance = True
        from group_bot.group_app import toggle_group_lock
        await toggle_group_lock(context, CHANNEL_ID, lock=True)
        
        await asyncio.sleep(duration_mins * 60)
        
        is_maintenance = False
        await toggle_group_lock(context, CHANNEL_ID, lock=False)
        await update.message.reply_text("✅ <b>Resume:</b> Services active.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def send_db_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the database file to the admin securely."""
    if update.effective_user.id != ADMIN_ID: 
        return
    db_path = "makaut.db"
    if os.path.exists(db_path):
        with open(db_path, 'rb') as db_file:
            await update.message.reply_document(document=db_file, caption="📂 Database Backup")
    else:
        await update.message.reply_text("❌ Database not found.")

async def update_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pulls latest code from GitHub and restarts the process."""
    if update.effective_user.id != ADMIN_ID: 
        return
    await update.message.reply_text("📥 <b>Admin:</b> Pulling from GitHub...")
    process = await asyncio.create_subprocess_shell("git pull origin main", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    if process.returncode == 0:
        await update.message.reply_text("✅ Code updated. Restarting system...")
        os.execv(sys.executable, ['python3'] + sys.argv)

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zenith Forensic Health Report with DB Metrics."""
    if update.effective_user.id != ADMIN_ID: 
        return
    cpu, ram = psutil.cpu_percent(), psutil.virtual_memory().percent
    async with AsyncSessionLocal() as db:
        total = (await db.execute(select(func.count(Notification.id)))).scalar()
        strikes = (await db.execute(select(func.count(UserStrike.user_id)))).scalar()
        status_msg = (
            f"<b>🖥️ ZENITH SYSTEM HEALTH</b>\n\n"
            f"📊 CPU: {cpu}% | 🧠 RAM: {ram}%\n"
            f"📁 Notices: {total} | 🚫 Violators: {strikes}\n"
            f"Mode: {'MAINTENANCE' if is_maintenance else 'LIVE'}"
        )
    await update.message.reply_text(status_msg, parse_mode='HTML')
    #@academictelebotbyroshhellwett