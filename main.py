import asyncio
import logging
import sys

from core.logger import setup_logger
from database.init_db import init_db
from bot.telegram_app import start_telegram
from pipeline.ingest_pipeline import start_pipeline
from search_bot.search_app import start_search_bot 
from admin_bot.admin_app import start_admin_bot 

# Initialize Logger
setup_logger()
logger = logging.getLogger("MAIN")

async def main():
    """
    Main entry point for the TeleAcademic System.
    Orchestrates the Triple-Bot architecture:
    1. Broadcast Bot (Channel updates)
    2. Search Bot (Student queries)
    3. Admin Bot (Script updates & management)
    """
    logger.info("🚀 TELEACADEMIC TRIPLE-BOT SYSTEM STARTING")

    # 1. Database Initialization
    try:
        init_db()
        logger.info("DATABASE TABLES VERIFIED")
    except Exception as e:
        logger.critical(f"DATABASE INIT FAILED: {e}")
        sys.exit(1)

    # 2. Start Broadcast Bot (Channel Bot)
    # This bot usually runs in the foreground of the loop or as a primary task
    try:
        await start_telegram()
        logger.info("BROADCAST BOT INITIALIZED")
    except Exception as e:
        logger.critical(f"BROADCAST BOT START FAILED: {e}")
        sys.exit(1)

    # 3. Start Search Bot Task
    # Runs in the background to handle student searches
    try:
        asyncio.create_task(start_search_bot()) 
        logger.info("SEARCH BOT TASK INITIALIZED")
    except Exception as e:
        logger.error(f"SEARCH BOT START FAILED: {e}")

    # 4. Start Admin Bot Task (The Script Updater)
    # Runs in the background to handle private /update and /backup commands
    try:
        asyncio.create_task(start_admin_bot()) 
        logger.info("ADMIN UPDATER BOT TASK INITIALIZED")
    except Exception as e:
        logger.error(f"ADMIN BOT START FAILED: {e}")

    # 5. Start Scraper Pipeline Task
    # Periodically checks for new notices and triggers broadcasts
    try:
        pipeline_task = asyncio.create_task(start_pipeline())
        logger.info("SCRAPER PIPELINE INITIALIZED")
    except Exception as e:
        logger.critical(f"PIPELINE START FAILED: {e}")
        sys.exit(1)

    logger.info("SYSTEM FULLY OPERATIONAL")

    # Keep the main loop running by awaiting the pipeline task
    try:
        await pipeline_task
    except Exception as e:
        logger.critical(f"SYSTEM CRASHED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SYSTEM SHUTDOWN BY USER")
        sys.exit(0)