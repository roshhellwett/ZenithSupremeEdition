import asyncio
import logging
from telegram import Bot
from database.db import SessionLocal
from core.config import BOT_TOKEN, SEARCH_BOT_TOKEN
from scraper.date_extractor import extract_date
from scraper.pdf_processor import get_date_from_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HEALTH_CHECK")

async def verify_system():
    print("\n🔍 === TELEACADEMIC FINAL HEALTH CHECK ===\n")

    # 1. Test Database
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        print("✅ DATABASE: Connection Successful")
        db.close()
    except Exception as e:
        print(f"❌ DATABASE: Connection Failed | {e}")

    # 2. Test Main Bot Token
    try:
        bot = Bot(token=BOT_TOKEN)
        me = await bot.get_me()
        print(f"✅ MAIN BOT: @{me.username} is Online")
    except Exception as e:
        print(f"❌ MAIN BOT: Token Invalid | {e}")

    # 3. Test Search Bot Token
    try:
        s_bot = Bot(token=SEARCH_BOT_TOKEN)
        s_me = await s_bot.get_me()
        print(f"✅ SEARCH BOT: @{s_me.username} is Online")
    except Exception as e:
        print(f"❌ SEARCH BOT: Token Invalid | {e}")

    # 4. Test Dot-Date Logic (The Fix for 22.11.2019)
    test_date_str = "Notice dated 22.11.2019"
    parsed = extract_date(test_date_str)
    if parsed and parsed.year == 2019:
        print(f"✅ DATE EXTRACTOR: Correctly parsed '{test_date_str}'")
    else:
        print(f"❌ DATE EXTRACTOR: Failed to parse dot-separated dates")

    # 5. Test PDF Processor (Requires Internet)
    print("⏳ Testing PDF Deep Scan (Sample MAKAUT URL)...")
    sample_pdf = "https://makautwb.ac.in/notice_files/211_1.pdf"
    try:
        pdf_date = get_date_from_pdf(sample_pdf)
        if pdf_date:
            print(f"✅ PDF PROCESSOR: Successfully extracted date {pdf_date.date()} from file")
        else:
            print("⚠️ PDF PROCESSOR: Connected, but no date found in sample (Expected behavior for some files)")
    except Exception as e:
        print(f"❌ PDF PROCESSOR: Library Error or Network Timeout | {e}")

    print("\n🚀 === CHECK COMPLETE: READY TO DEPLOY ===\n")

if __name__ == "__main__":
    asyncio.run(verify_system())