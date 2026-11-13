from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import AsyncSessionLocal
from services.data_fetcher import fetch_and_update_all
import logging

logger = logging.getLogger("uvicorn.error")
scheduler = AsyncIOScheduler()


async def refresh_job():
    logger.info("[scheduler] Running scheduled data refresh...")
    async with AsyncSessionLocal() as db:
        try:
            await fetch_and_update_all(db)
        except Exception as e:
            logger.error(f"[scheduler] Refresh failed: {e}")


def start_scheduler():
    if scheduler.running:
        logger.info("[scheduler] Already running; skipping duplicate start")
        return

    scheduler.add_job(
        refresh_job,
        "interval",
        minutes=30,
        id="data_refresh",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("[scheduler] Background refresh scheduler started (every 30 min)")
