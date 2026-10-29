"""Command-line entry point: python -m app.scraper [--recent N]"""

import argparse
import logging
import time
from collections import Counter
from pathlib import Path

import httpx
from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal
from app.models import Bout, Event, Fighter
from app.scraper.fetcher import Fetcher
from app.scraper.loader import save_event
from app.scraper.parsers import (
    EVENT_LIST_URL,
    ParsedFighter,
    parse_event_list,
    parse_event_page,
    parse_fighter_page,
)

log = logging.getLogger("scraper")


def run(recent: int) -> Counter:
    """Scrape all upcoming events plus the `recent` latest past events into the database."""
    if not settings.scraper_contact:
        raise SystemExit(
            "Set SCRAPER_CONTACT (an email or URL) in .env first. Wikipedia's User-Agent "
            "policy requires bots to say how to reach their operator."
        )
    # Format required by https://meta.wikimedia.org/wiki/User-Agent_policy
    user_agent = (
        f"FightNightContentTracker/0.1 ({settings.scraper_contact}) httpx/{httpx.__version__}"
    )
    fetcher = Fetcher(
        cache_dir=Path(settings.scraper_cache_dir),
        delay_seconds=settings.scraper_delay_seconds,
        cache_hours=settings.scraper_cache_hours,
        user_agent=user_agent,
    )
    stats: Counter = Counter()
    fighter_details: dict[str, ParsedFighter | None] = {}

    try:
        upcoming, past = parse_event_list(fetcher.get(EVENT_LIST_URL), recent=recent)
        log.info("Found %d upcoming and %d recent events", len(upcoming), len(past))

        for url in upcoming + past:
            try:
                parsed = parse_event_page(fetcher.get(url))
            except (httpx.HTTPError, ValueError) as exc:
                log.warning("Skipping event %s: %s", url, exc)
                stats["events_failed"] += 1
                continue

            for bout in parsed.bouts:
                for link in (bout.left, bout.right):
                    if link.has_page and link.url not in fighter_details:
                        fighter_details[link.url] = _fetch_fighter(fetcher, link.url, stats)

            # One transaction per event: a failure later on keeps the events already saved.
            with SessionLocal() as session:
                save_event(session, url, parsed, fighter_details, stats)
                session.commit()
            log.info("Saved %s (%s, %d bouts)", parsed.name, parsed.date, len(parsed.bouts))
    finally:
        fetcher.close()

    stats["http_requests"] = fetcher.requests_made
    stats["cache_hits"] = fetcher.cache_hits
    return stats


def _fetch_fighter(fetcher: Fetcher, url: str, stats: Counter) -> ParsedFighter | None:
    try:
        return parse_fighter_page(fetcher.get(url), url)
    except httpx.HTTPError as exc:
        log.warning("Could not fetch fighter %s: %s", url, exc)
        stats["fighters_failed"] += 1
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape UFC events from Wikipedia.")
    parser.add_argument(
        "--recent", type=int, default=10, help="how many past events to include (default 10)"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    started = time.perf_counter()
    stats = run(recent=args.recent)
    elapsed = time.perf_counter() - started

    with SessionLocal() as session:
        totals = {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (Event, Bout, Fighter)
        }
    print(f"\nFinished in {elapsed:.1f}s")
    for key in sorted(stats):
        print(f"  {key}: {stats[key]}")
    print(f"  Database totals: {totals}")


if __name__ == "__main__":
    main()
