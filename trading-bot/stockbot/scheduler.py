"""Background schedule (America/New_York): intraday checks every N minutes + official-close checks."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from stockbot.alerts.engine import run_check
from stockbot.alerts.notifier import send_alert
from stockbot.config import settings
from stockbot.data.market import ET

log = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone=ET)


def _job(mode: str) -> None:
    try:
        report = run_check(mode, sender=send_alert)
        log.info("check %s: tickers=%s alerts=%s stale=%s skipped=%s", mode, report.tickers,
                 len(report.alerts), len(report.stale), report.skipped)
    except Exception:
        log.exception("check %s crashed", mode)


def start() -> None:
    every = max(5, settings.check_interval_minutes)
    # 09:30 … 15:30 ET on weekdays; holidays/half-days are skipped via the live market-status check.
    scheduler.add_job(_job, CronTrigger(day_of_week="mon-fri", hour="9-15", minute=f"*/{every}", timezone=ET),
                      args=["intraday"], id="intraday", max_instances=1, coalesce=True, replace_existing=True)
    # Official close: Yahoo publishes the completed daily candle ~16:20 ET; run twice (deduplicated) to be safe.
    scheduler.add_job(_job, CronTrigger(day_of_week="mon-fri", hour="16,17", minute=35, timezone=ET),
                      args=["close"], id="close", max_instances=1, coalesce=True, replace_existing=True)
    scheduler.start()
    log.info("scheduler started (every %s min + close)", every)


def stop() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
