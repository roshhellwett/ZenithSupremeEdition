import asyncio
import logging
import sys

from core.logger import setup_logger
from database.init_db import init_db
from bot.telegram_app import start_telegram, get_bot # Added get_bot
from pipeline.ingest_pipeline import start_pipeline
from search_bot.search_app import start_search_bot 
from admin_bot.admin_app import start_admin_bot 
from group_bot.group_app import start_group_bot
from core.config import ADMIN_ID # Ensure ADMIN_ID is imported

setup_logger()
logger = logging.getLogger("MAIN")

async def main():
    logger.info("🚀 ACADEMIC TELE-BOT SYSTEM STARTING")

    # 1. Database Initialization
    try:
        await init_db()
        logger.info("DATABASE TABLES VERIFIED")
    except Exception as e:
        logger.critical(f"DATABASE INIT FAILED: {e}")
        sys.exit(1)

    # 2. Start Broadcast Bot
    try:
        await start_telegram()
        logger.info("BROADCAST BOT INITIALIZED")
    except Exception as e:
        logger.critical(f"BROADCAST BOT START FAILED: {e}")
        sys.exit(1)

    # NEW: Admin Restart Notification
    # This sends a message to you only after the bot is fully ready
    if ADMIN_ID != 0:
        try:
            bot = get_bot()
            await bot.send_message(
                chat_id=ADMIN_ID, 
                text="✅ <b>System Online:</b> Update successful. All services are back and monitoring.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Could not send restart notification: {e}")

    # 3. Launch background services
    logger.info("STARTING BACKGROUND SERVICES...")
    
    try:
        search_task = asyncio.create_task(start_search_bot())
        await asyncio.sleep(2)
        
        admin_task = asyncio.create_task(start_admin_bot())
        await asyncio.sleep(2)
        
        group_task = asyncio.create_task(start_group_bot())
        await asyncio.sleep(2)
        
        pipeline_task = asyncio.create_task(start_pipeline())

        await asyncio.gather(search_task, admin_task, group_task, pipeline_task)
    except Exception as e:
        logger.critical(f"SYSTEM CRITICAL FAILURE: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SYSTEM SHUTDOWN BY USER")
        sys.exit(0)
        #@academictelebotbyroshhellwett