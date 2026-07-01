import asyncio
import logging
from app.core.config import Settings
from app.db.session import AsyncSessionLocal
from app.ingestion.email_intake import EmailIntakeService

logger = logging.getLogger(__name__)


class EmailIntakeWorker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._stopped = asyncio.Event()

    async def run(self) -> None:
        if not self.settings.email_intake_enabled:
            logger.info("Email intake worker is disabled by config. Background polling will not start.")
            return

        logger.info("Email intake worker started. Polling interval: %s seconds.", self.settings.email_intake_poll_interval_seconds)
        while not self._stopped.is_set():
            try:
                async with AsyncSessionLocal() as db:
                    service = EmailIntakeService(self.settings)
                    try:
                        stats = await service.sync_emails(db)
                        if stats["status"] == "success" and stats["scanned_emails"] > 0:
                            logger.info("Email intake sync completed: scanned=%s, imported=%s, skipped=%s, failed=%s",
                                        stats["scanned_emails"], stats["imported_emails"], 
                                        stats["skipped_emails"], stats["failed_emails"])
                    except Exception as e:
                        logger.exception("Error executing email sync loop: %s", e)
            except Exception as e:
                logger.exception("Email intake worker database session failed: %s", e)

            # Wait for next poll interval or stop event
            try:
                await asyncio.wait_for(
                    self._stopped.wait(), 
                    timeout=float(self.settings.email_intake_poll_interval_seconds)
                )
            except (TimeoutError, asyncio.TimeoutError):
                pass

    def stop(self) -> None:
        logger.info("Stopping email intake worker...")
        self._stopped.set()
