import asyncio
import logging
from scraper.makaut_scraper import scrape_source
from core.sources import URLS
from database.repository import NotificationRepo
from delivery.channel_broadcaster import broadcast_channel
from pipeline.message_formatter import format_message
from core.config import SCRAPE_INTERVAL

logger = logging.getLogger("PIPELINE")

async def start_pipeline():
    logger.info("🚀 PIPELINE: STARTED (Ordering: Oldest -> Newest)")
    
    while True:
        cycle_start = asyncio.get_event_loop().time()
        
        for key, config in URLS.items():
            try:
                # 1. Scrape (Returns Newest First usually)
                items = await scrape_source(key, config)
                
                if not items:
                    continue

                items.sort(key=lambda x: x['published_date'], reverse=False)
                
                new_notices = []
                for item in items:
                    # 3. Check DB (Atomic Check-and-Insert)
                    is_new = await NotificationRepo.add_notification(item)
                    if is_new:
                        logger.info(f"📥 NEW NOTICE LOCKED: {item['title'][:40]}...")
                        new_notices.append(format_message(item))
                
                # 4. Broadcast Batch (Strictly Ordered)
                if new_notices:
                    logger.info(f"📢 Broadcasting {len(new_notices)} new items...")
                    await broadcast_channel(new_notices)
                
                # Nice to University Server
                await asyncio.sleep(2)  

            except Exception as e:
                logger.error(f"❌ PIPELINE ERROR [{key}]: {e}", exc_info=True)

        # Smart Sleep
        elapsed = asyncio.get_event_loop().time() - cycle_start
        sleep_time = max(10, SCRAPE_INTERVAL - elapsed)
        logger.info(f"💤 Pipeline Sleeping {int(sleep_time)}s...")
        await asyncio.sleep(sleep_time)
        #@academictelebotbyroshhellwett