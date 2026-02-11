import asyncio
import logging
import sys

from core.logger import setup_logger
from database.init_db import init_db
from bot.telegram_app import start_telegram
from pipeline.ingest_pipeline import start_pipeline
from search_bot.search_app import start_search_bot 

logger = logging.getLogger("MAIN")

async def main():
    setup_logger()
    logger.info("🚀 TELEACADEMIC DUAL-BOT SYSTEM STARTING")

    # 1. Database Initialization
    try:
        init_db()
    except Exception as e:
        logger.critical(f"DATABASE INIT FAILED: {e}")
        sys.exit(1)

    # 2. Start Broadcast Bot
    try:
        await start_telegram()
    except Exception as e:
        logger.critical(f"BROADCAST BOT START FAILED: {e}")
        sys.exit(1)

    # 3. Start Search Bot (Runs as background task)
    try:
        asyncio.create_task(start_search_bot()) 
        logger.info("SEARCH BOT TASK INITIALIZED")
    except Exception as e:
        logger.error(f"SEARCH BOT START FAILED: {e}")

    # 4. Start Scraper Pipeline
    pipeline_task = asyncio.create_task(start_pipeline())

    logger.info("DUAL-BOT SYSTEM READY")

    try:
        await pipeline_task
    except Exception as e:
        logger.critical(f"SYSTEM CRASHED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass