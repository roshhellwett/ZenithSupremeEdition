import asyncio
import logging
from sqlalchemy import select
from scraper.makaut_scraper import scrape_source, get_source_health
from core.sources import URLS
from database.db import AsyncSessionLocal
from database.models import Notification
from delivery.channel_broadcaster import broadcast_channel
from pipeline.message_formatter import format_message
from core.config import SCRAPE_INTERVAL, ADMIN_ID
from bot.telegram_app import get_bot

logger = logging.getLogger("PIPELINE")

async def start_pipeline():
    """Main background task with heartbeat monitoring and maintenance suspension."""
    logger.info("🚀 SUPREME ASYNC PIPELINE STARTED")
    
    while True:
        # Maintenance Lock Check: Pauses scraping if Admin has engaged maintenance mode
        from admin_bot.handlers import is_maintenance
        if is_maintenance:
            logger.info("⏸️ PIPELINE PAUSED: Maintenance Mode Active")
            await asyncio.sleep(10)
            continue

        cycle_start = asyncio.get_event_loop().time()
        logger.info("🔄 Starting new scrape cycle...")
        
        try:
            for key, config in URLS.items():
                logger.info(f"📡 Scraping source: {key} ({config['source']})")
                
                try:
                    items = await scrape_source(key, config)
                except Exception as e:
                    logger.error(f"❌ SCRAPER FAILED FOR {key}: {e}")
                    continue
                
                if not items:
                    logger.info(f"ℹ️ NO NEW ITEMS FOUND {key}")
                    continue

                logger.info(f"✅ FOUND {len(items)} ITEMS {key}. CHECKING DATABASE...")
                
                async with AsyncSessionLocal() as db:
                    new_count = 0
                    for item in items:
                        # Check for existing notice using hash deduplication
                        stmt = select(Notification.id).where(Notification.content_hash == item['content_hash'])
                        result = await db.execute(stmt)
                        exists = result.scalar()

                        if not exists:
                            db.add(Notification(**item))
                            await db.commit() 
                            
                            # Deliver to notification channel
                            await broadcast_channel([format_message(item)])
                            new_count += 1
                    
                    if new_count > 0:
                        logger.info(f"📢 BROADCASTED {new_count} NEW NOTICES FROM {key}")
                
                await asyncio.sleep(3)
            
            # Health Check: Alert Admin if a university source fails repeatedly
            health = get_source_health()
            for src, fails in health.items():
                if fails >= 3:
                    logger.warning(f"⚠️ SOURCE {src} IS REPORTING FAILURE: {fails}")
                    try:
                        bot = get_bot()
                        await bot.send_message(
                            ADMIN_ID, 
                            f"🚨 <b>SOURCE DOWN ALERT</b>\nSource: {src}\nFails: {fails}", 
                            parse_mode="HTML"
                        )
                    except:
                        pass
                
        except Exception as e:
            logger.error(f"❌ GLOBAL PIPELINE LOOP ERROR: {e}")
        
        # Dynamic Scheduling: Calculate sleep time based on cycle duration
        elapsed = asyncio.get_event_loop().time() - cycle_start
        sleep_time = max(10, SCRAPE_INTERVAL - elapsed)
        
        logger.info(f"💤 CYCLE COMPLETE IN {int(elapsed)}s. NEXT CYCLE IN {int(sleep_time)}s...")
        await asyncio.sleep(sleep_time)
        #@academictelebotbyroshhellwett