"""Tests that saving scraped data is idempotent: re-running updates instead of duplicating."""

import datetime as dt
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Bout, CardPosition, Event, Fighter, FootageStatus
from app.scraper.loader import save_event
from app.scraper.parsers import FighterLink, ParsedBout, ParsedEvent, ParsedFighter

EVENT_URL = "https://en.wikipedia.org/wiki/UFC_999"
RED = FighterLink("Red Fighter", "https://en.wikipedia.org/wiki/Red_Fighter", has_page=True)
BLUE = FighterLink("Blue Fighter", "https://en.wikipedia.org/wiki/Blue_Fighter", has_page=True)


def make_parsed_event(bout: ParsedBout) -> ParsedEvent:
    return ParsedEvent(name="UFC 999", date=dt.date(2027, 1, 9), location="Las Vegas", bouts=[bout])


def upcoming_bout() -> ParsedBout:
    return ParsedBout("Lightweight", RED, BLUE, CardPosition.MAIN, None, None, None)


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_saving_twice_does_not_duplicate(db: Session) -> None:
    parsed = make_parsed_event(upcoming_bout())

    save_event(db, EVENT_URL, parsed, {}, Counter())
    stats = Counter()
    save_event(db, EVENT_URL, parsed, {}, stats)

    assert (count(db, Event), count(db, Bout), count(db, Fighter)) == (1, 1, 2)
    assert stats == {"events_unchanged": 1, "fighters_unchanged": 2, "bouts_unchanged": 1}


def test_changed_details_are_updated(db: Session) -> None:
    save_event(db, EVENT_URL, make_parsed_event(upcoming_bout()), {}, Counter())

    moved = make_parsed_event(upcoming_bout())
    moved.location = "Abu Dhabi"
    stats = Counter()
    event = save_event(db, EVENT_URL, moved, {}, stats)

    assert event.location == "Abu Dhabi"
    assert stats["events_updated"] == 1


def test_winner_moving_to_the_left_matches_the_existing_bout(db: Session) -> None:
    save_event(db, EVENT_URL, make_parsed_event(upcoming_bout()), {}, Counter())

    # After the fight, Wikipedia lists the winner (Blue) first.
    finished = ParsedBout("Lightweight", BLUE, RED, CardPosition.MAIN, "left_won", "KO (punch)", 1)
    save_event(db, EVENT_URL, make_parsed_event(finished), {}, Counter())

    bout = db.scalar(select(Bout))
    assert count(db, Bout) == 1
    assert bout.red_fighter.name == "Red Fighter"  # corners kept from the first save
    assert (bout.result, bout.method, bout.round) == ("blue", "KO (punch)", 1)


def test_rescrape_keeps_the_teams_footage_status(db: Session) -> None:
    save_event(db, EVENT_URL, make_parsed_event(upcoming_bout()), {}, Counter())
    bout = db.scalar(select(Bout))
    bout.footage.status = FootageStatus.DELIVERED
    bout.footage.notes = "Sent to social team"
    db.flush()

    save_event(db, EVENT_URL, make_parsed_event(upcoming_bout()), {}, Counter())

    assert bout.footage.status == FootageStatus.DELIVERED
    assert bout.footage.notes == "Sent to social team"


def test_new_bout_starts_with_planned_footage(db: Session) -> None:
    save_event(db, EVENT_URL, make_parsed_event(upcoming_bout()), {}, Counter())

    assert db.scalar(select(Bout)).footage.status == FootageStatus.PLANNED


def test_fighter_details_and_canonical_url(db: Session) -> None:
    # The card links to a redirect; the fighter's page says its real (canonical) URL.
    redirect = FighterLink("Red Fighter", "https://en.wikipedia.org/wiki/Red_F", has_page=True)
    details = ParsedFighter(RED.url, nickname="The Red", record="10-2-0", weight_class=None)
    bout = ParsedBout("Lightweight", redirect, BLUE, CardPosition.MAIN, None, None, None)

    save_event(db, EVENT_URL, make_parsed_event(bout), {redirect.url: details}, Counter())

    fighter = db.scalar(select(Fighter).where(Fighter.name == "Red Fighter"))
    assert fighter.source_url == RED.url
    assert (fighter.nickname, fighter.record) == ("The Red", "10-2-0")
    assert fighter.weight_class == "Lightweight"  # filled in from the bout
