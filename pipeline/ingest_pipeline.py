import asyncio
import logging
import os
from datetime import datetime
from sqlalchemy import text

from scraper.makaut_scraper import scrape_source, get_source_health
from core.sources import URLS
from database.db import SessionLocal
from database.models import Notification, SystemFlag
from delivery.channel_broadcaster import broadcast_channel
from pipeline.message_formatter import format_message
from core.config import SCRAPE_INTERVAL, ADMIN_ID
from bot.telegram_app import get_bot

logger = logging.getLogger("PIPELINE")
FAILURE_THRESHOLD = 3 # Alert after 3 consecutive fails

async def check_source_health():
    """Supreme God Mode: Alerts Admin if a source is consistently failing."""
    health = get_source_health()
    bot = get_bot()
    
    for source, fails in health.items():
        if fails == FAILURE_THRESHOLD:
            alert_msg = f"⚠️ <b>SUPREME ALERT: SOURCE DOWN</b>\n\nSource: <code>{source}</code>\nStatus: Failed {fails} times.\nAction: Investigate university website."
            try:
                await bot.send_message(chat_id=ADMIN_ID, text=alert_msg, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send health alert: {e}")

async def maintain_db():
    """Weekly Database Optimization."""
    now = datetime.utcnow()
    if now.weekday() == 6 and now.hour == 0 and now.minute < 10:
        db = SessionLocal()
        try:
            logger.info("🧹 Supreme Maintenance: Database VACUUM.")
            db.execute(text("VACUUM"))
            db.commit()
        except Exception as e:
            logger.error(f"Maintenance Error: {e}")
        finally:
            db.close()

async def start_pipeline():
    """Main background task for the notification pipeline[cite: 103]."""
    logger.info("PIPELINE STARTED")
    await asyncio.sleep(5)

    while True:
        db = None
        try:
            await maintain_db()
            logger.info("SCRAPE CYCLE START")
            all_scraped_items = []
            
            for key, config in URLS.items():
                logger.info(f"SCRAPING SOURCE: {key}")
                source_data = scrape_source(key, config)
                all_scraped_items.extend(source_data)
                await asyncio.sleep(2) 

            # Check health after each cycle [cite: 105]
            await check_source_health()

            if not all_scraped_items:
                await asyncio.sleep(int(SCRAPE_INTERVAL))
                continue

            all_scraped_items.sort(key=lambda x: x['published_date'])
            db = SessionLocal()
            
            existing_hashes = {
                h for (h,) in db.query(Notification.content_hash)
                .order_by(Notification.id.desc())
                .limit(5000)
                .all()
            }

            new_notifications = []
            notifications_to_save = []

            for item in all_scraped_items:
                h = item.get("content_hash")
                if not h or h in existing_hashes:
                    continue
                notif = Notification(**item)
                notifications_to_save.append(notif)
                new_notifications.append(item)
                existing_hashes.add(h)

            if not new_notifications:
                db.close()
                await asyncio.sleep(int(SCRAPE_INTERVAL))
                continue

            first_flag = db.query(SystemFlag).filter_by(key="FIRST_RUN_DONE").first()
            if not first_flag:
                items_to_send = new_notifications[:20]
                db.add(SystemFlag(key="FIRST_RUN_DONE", value="1"))
            else:
                items_to_send = new_notifications

            if items_to_send:
                await broadcast_channel([format_message(n) for n in items_to_send])

            for n_obj in notifications_to_save:
                db.add(n_obj)
            db.commit()

        except Exception as e:
            logger.error(f"PIPELINE ERROR: {e}", exc_info=True)
            if db: db.rollback()
        finally:
            if db: db.close()

        await asyncio.sleep(int(SCRAPE_INTERVAL))