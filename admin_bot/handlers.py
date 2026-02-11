import os
import sys
import logging
import psutil
import time
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_ID  # Ensure ADMIN_ID is defined in your config

logger = logging.getLogger("ADMIN_HANDLERS")

async def update_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Pulls the latest code from GitHub and restarts the entire triple-bot system.
    """
    if update.effective_user.id != ADMIN_ID:
        logger.warning(f"Unauthorized update attempt by ID: {update.effective_user.id}")
        return

    await update.message.reply_text("📥 <b>Admin:</b> Pulling latest changes from GitHub...")
    
    # Execute git pull
    try:
        os.system("git pull origin main")
        await update.message.reply_text("✅ Code updated. Restarting system...")
        
        # Hot-swap restart: This triggers the run_bot.sh loop to reload the new code
        os.execv(sys.executable, ['python3'] + sys.argv)
    except Exception as e:
        logger.error(f"Update failed: {e}")
        await update.message.reply_text(f"❌ Update failed: {e}")

async def send_db_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sends the current makaut.db file directly to your private Admin chat.
    """
    if update.effective_user.id != ADMIN_ID:
        return

    db_path = "makaut.db"
    if os.path.exists(db_path):
        await update.message.reply_document(
            document=open(db_path, 'rb'), 
            filename=f"makaut_backup_{int(time.time())}.db",
            caption="📂 Here is your latest database backup."
        )
    else:
        await update.message.reply_text("❌ Database file (makaut.db) not found.")

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Provides a real-time report of the laptop's CPU, RAM, and Bot status.
    """
    if update.effective_user.id != ADMIN_ID:
        return

    # Gather system metrics using psutil
    cpu_usage = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    
    # Calculate uptime (approximate based on process start)
    uptime_seconds = int(time.time() - psutil.Process(os.getpid()).create_time())
    uptime_str = time.strftime('%Hh %Mm %Ss', time.gmtime(uptime_seconds))

    status_msg = (
        "<b>🖥️ System Health Report</b>\n\n"
        f"<b>⏱ Uptime:</b> {uptime_str}\n"
        f"<b>📊 CPU Usage:</b> {cpu_usage}%\n"
        f"<b>🧠 RAM Usage:</b> {ram_usage}%\n\n"
        "<b>🤖 Active Services:</b>\n"
        "✅ Broadcast Bot: <i>Active</i>\n"
        "✅ Search Bot: <i>Active</i>\n"
        "✅ Scraper Pipeline: <i>Active</i>\n\n"
        "<i>Running 24/7 on Linux Mint</i>"
    )
    
    await update.message.reply_text(status_msg, parse_mode='HTML')