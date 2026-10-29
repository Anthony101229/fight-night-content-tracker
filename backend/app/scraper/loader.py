"""Save parsed data to the database. Every function here is safe to run again and again.

Each record is looked up by a stable key first (a Wikipedia URL, or the two fighters
in a bout). If it exists it is updated in place; otherwise it is created.
"""

from collections import Counter

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import Base, Bout, Event, Fighter, FootageAsset
from app.scraper.parsers import FighterLink, ParsedBout, ParsedEvent, ParsedFighter


def save_event(
    session: Session,
    source_url: str,
    parsed: ParsedEvent,
    fighter_details: dict[str, ParsedFighter | None],
    stats: Counter,
) -> Event:
    """Create or update one event, its fighters and its bouts. Does not commit."""
    event = session.scalar(select(Event).where(Event.source_url == source_url))
    created = event is None
    if created:
        event = Event(source_url=source_url)
        session.add(event)
    event.name = parsed.name
    event.date = parsed.date
    event.location = parsed.location
    _count(session, stats, "events", event, created)
    session.flush()  # assigns event.id, needed by the bout lookups below

    for parsed_bout in parsed.bouts:
        left = _save_fighter(
            session, parsed_bout.left, fighter_details.get(parsed_bout.left.url),
            parsed_bout.weight_class, stats,
        )
        right = _save_fighter(
            session, parsed_bout.right, fighter_details.get(parsed_bout.right.url),
            parsed_bout.weight_class, stats,
        )
        _save_bout(session, event, left, right, parsed_bout, stats)
    return event


def _save_fighter(
    session: Session,
    link: FighterLink,
    details: ParsedFighter | None,
    weight_class_hint: str | None,
    stats: Counter,
) -> Fighter:
    # The canonical URL merges redirects, e.g. two spellings of one fighter's name.
    url = details.canonical_url if details else link.url
    fighter = session.scalar(select(Fighter).where(Fighter.source_url == url))
    created = fighter is None
    if created:
        fighter = Fighter(source_url=url)
        session.add(fighter)

    fighter.name = link.name
    if details:
        fighter.nickname = details.nickname
        fighter.record = details.record
        fighter.weight_class = details.weight_class or fighter.weight_class
    if not fighter.weight_class:
        fighter.weight_class = weight_class_hint  # fall back to this bout's division

    _count(session, stats, "fighters", fighter, created)
    session.flush()  # assigns fighter.id
    return fighter


def _save_bout(
    session: Session,
    event: Event,
    left: Fighter,
    right: Fighter,
    parsed: ParsedBout,
    stats: Counter,
) -> Bout:
    # Match the pair in either order: once a fight happens Wikipedia moves the winner
    # to the left, which would otherwise look like a brand-new bout.
    bout = session.scalar(
        select(Bout).where(
            Bout.event_id == event.id,
            or_(
                and_(Bout.red_fighter_id == left.id, Bout.blue_fighter_id == right.id),
                and_(Bout.red_fighter_id == right.id, Bout.blue_fighter_id == left.id),
            ),
        )
    )
    created = bout is None
    if created:
        # New bouts start with a "planned" footage record for the team to update.
        bout = Bout(event=event, red_fighter=left, blue_fighter=right, footage=FootageAsset())
        session.add(bout)

    bout.weight_class = parsed.weight_class
    bout.card_position = parsed.card_position
    bout.method = parsed.method
    bout.round = parsed.round
    if parsed.outcome == "left_won":
        bout.result = "red" if bout.red_fighter is left else "blue"
    else:
        bout.result = parsed.outcome  # "draw", "no_contest" or None

    _count(session, stats, "bouts", bout, created)
    return bout


def _count(session: Session, stats: Counter, kind: str, obj: Base, created: bool) -> None:
    if created:
        stats[f"{kind}_created"] += 1
    elif session.is_modified(obj, include_collections=False):
        stats[f"{kind}_updated"] += 1
    else:
        stats[f"{kind}_unchanged"] += 1
