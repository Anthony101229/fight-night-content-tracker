"""Helpers that create test data."""

import datetime as dt

from sqlalchemy.orm import Session

from app.models import Bout, CardPosition, Event, Fighter, FootageAsset


def make_event(
    db: Session,
    name: str = "UFC Test Night",
    days_from_today: int = 7,
    positions: tuple[CardPosition, ...] = (CardPosition.MAIN,),
) -> Event:
    """Create an event with one bout (and footage record) per card position."""
    event = Event(
        name=name,
        date=dt.date.today() + dt.timedelta(days=days_from_today),
        location="Las Vegas, Nevada",
        source_url=f"https://en.wikipedia.org/wiki/{name.replace(' ', '_')}",
    )
    for i, position in enumerate(positions):
        red = Fighter(name=f"{name} Red {i}", source_url=f"{event.source_url}/red{i}")
        blue = Fighter(name=f"{name} Blue {i}", source_url=f"{event.source_url}/blue{i}")
        event.bouts.append(
            Bout(red_fighter=red, blue_fighter=blue, card_position=position, footage=FootageAsset())
        )
    db.add(event)
    db.flush()
    # Forget the in-memory objects so API calls load fresh from the database, like real requests.
    db.expire_all()
    return event
