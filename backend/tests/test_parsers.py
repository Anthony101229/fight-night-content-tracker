"""Tests for the Wikipedia HTML parsers, using small hand-written pages.

Each snippet copies the structure of the real Wikipedia pages, including the awkward
cases the parsers have to handle.
"""

import datetime as dt

from app.models import CardPosition
from app.scraper.parsers import parse_event_list, parse_event_page, parse_fighter_page

EVENT_LIST_HTML = """
<h2 id="Scheduled_events">Scheduled events</h2>
<table>
  <tr><th>Event</th><th>Date</th><th>Venue</th></tr>
  <tr><td><a href="/wiki/UFC_401">UFC 401</a></td><td>Jan 9, 2027</td><td><a href="/wiki/Arena_A">Arena A</a></td></tr>
  <!-- No article for this event yet: the parser must not pick up the venue link instead. -->
  <tr><td>UFC Fight Night 300</td><td>Jan 2, 2027</td><td><a href="/wiki/Arena_B">Arena B</a></td></tr>
</table>
<h2 id="Past_events">Past events</h2>
<table>
  <tr><th>#</th><th>Event</th><th>Date</th></tr>
  <tr><td>3</td><td><a href="/wiki/UFC_400">UFC 400</a></td><td>Dec 5, 2026</td></tr>
  <tr><td>2</td><td><a href="/wiki/UFC_399">UFC 399</a></td><td>Nov 28, 2026</td></tr>
  <tr><td>1</td><td><a href="/wiki/UFC_398">UFC 398</a></td><td>Nov 21, 2026</td></tr>
</table>
"""

EVENT_HTML = """
<html><head><title>UFC 999 - Wikipedia</title></head><body>
<h1 id="firstHeading"><span>UFC 999</span></h1>
<table class="infobox">
  <tr><th>Date</th><td>December 7, 2024<span style="display:none"> (<span class="bday dtstart">2024-12-07</span>)</span></td></tr>
  <tr><th>Venue</th><td>T-Mobile Arena</td></tr>
  <tr><th>City</th><td><a href="/wiki/Paradise,_Nevada">Paradise, Nevada</a> , United States<sup>[1]</sup></td></tr>
</table>
<table class="toccolours">
  <tr><th colspan="8">Main card (PPV)</th></tr>
  <tr><th>Weight class</th><th></th><th></th><th></th><th>Method</th><th>Round</th><th>Time</th><th>Notes</th></tr>
  <tr><td>Flyweight</td><td><a href="/wiki/Alexandre_Pantoja">Alexandre Pantoja</a> (c)</td><td>def.</td>
      <td><a href="/wiki/Kai_Asakura">Kai Asakura</a></td><td>Submission (rear-naked choke)</td><td>2</td><td>2:05</td><td><sup>[a]</sup></td></tr>
  <tr><td>Welterweight</td><td><a href="/wiki/Shavkat_Rakhmonov">Shavkat Rakhmonov</a></td><td>def.</td>
      <td><a href="/wiki/Ian_Machado_Garry">Ian Machado Garry</a></td><td>Decision (unanimous) (48–47, 48–47, 48–47)</td><td>5</td><td>5:00</td><td></td></tr>
  <tr><td>Heavyweight</td><td><a href="/wiki/Ciryl_Gane">Ciryl Gane</a></td><td>vs.</td>
      <td><a href="/wiki/Alexander_Volkov">Alexander Volkov</a></td><td>Draw (majority) (29–28, 28–28, 28–28)</td><td>3</td><td>5:00</td><td></td></tr>
  <tr><th colspan="8">Preliminary card (ESPN)</th></tr>
  <tr><td>Lightweight</td>
      <td><a class="new" href="/w/index.php?title=Some_Prospect&amp;action=edit&amp;redlink=1">Some Prospect</a></td><td>vs.</td>
      <td>Plain Name (c)</td><td></td><td></td><td></td><td></td></tr>
</table>
</body></html>
"""

FIGHTER_HTML = """
<html><head><link rel="canonical" href="https://en.wikipedia.org/wiki/Charles_Oliveira"></head><body>
<table class="infobox">
  <tr><th>Other names</th><td>do Bronx</td></tr>
  <tr><th>Division</th><td><style>.plainlist ul{list-style:none}</style><div class="plainlist"><ul>
      <li>Featherweight (2012–2016)</li><li>Lightweight (2017–present)</li></ul></div></td></tr>
  <tr><th colspan="2">Mixed martial arts record</th></tr>
  <tr><th>Total</th><td>49</td></tr>
  <tr><th>Wins</th><td>37</td></tr>
  <tr><th>By knockout</th><td>10</td></tr>
  <tr><th>Losses</th><td>11 <sup>[2]</sup></td></tr>
  <tr><th>No contests</th><td>1</td></tr>
  <tr><th colspan="2">Kickboxing record</th></tr>
  <tr><th>Wins</th><td>99</td></tr>
</table>
</body></html>
"""


def test_event_list_returns_upcoming_and_recent_past() -> None:
    upcoming, past = parse_event_list(EVENT_LIST_HTML, recent=2)

    assert upcoming == ["https://en.wikipedia.org/wiki/UFC_401"]
    assert past == [
        "https://en.wikipedia.org/wiki/UFC_400",
        "https://en.wikipedia.org/wiki/UFC_399",
    ]


def test_event_page_details() -> None:
    event = parse_event_page(EVENT_HTML)

    assert event.name == "UFC 999"
    assert event.date == dt.date(2024, 12, 7)
    assert event.location == "T-Mobile Arena, Paradise, Nevada, United States"


def test_event_page_card_positions() -> None:
    event = parse_event_page(EVENT_HTML)

    assert [b.card_position for b in event.bouts] == [
        CardPosition.MAIN,
        CardPosition.CO_MAIN,
        CardPosition.MAIN_CARD,
        CardPosition.PRELIM,
    ]


def test_event_page_results() -> None:
    main, co_main, draw, upcoming = parse_event_page(EVENT_HTML).bouts

    assert (main.outcome, main.method, main.round) == (
        "left_won",
        "Submission (rear-naked choke)",
        2,
    )
    assert co_main.method == "Decision (unanimous)"  # judges' scores removed
    assert (draw.outcome, draw.method) == ("draw", "Draw (majority)")
    assert (upcoming.outcome, upcoming.method, upcoming.round) == (None, None, None)


def test_event_page_fighter_links() -> None:
    main, _, _, prelim = parse_event_page(EVENT_HTML).bouts

    assert main.left.name == "Alexandre Pantoja"  # "(c)" champion marker not included
    assert main.left.url == "https://en.wikipedia.org/wiki/Alexandre_Pantoja"
    assert main.left.has_page
    # Red link (no article) and plain text: still get a stable URL key, but no page to fetch.
    assert (prelim.left.name, prelim.left.has_page) == ("Some Prospect", False)
    assert prelim.left.url == "https://en.wikipedia.org/wiki/Some_Prospect"
    assert (prelim.right.name, prelim.right.has_page) == ("Plain Name", False)


def test_fighter_page() -> None:
    fighter = parse_fighter_page(FIGHTER_HTML, "https://en.wikipedia.org/wiki/Do_Bronx")

    assert fighter.canonical_url == "https://en.wikipedia.org/wiki/Charles_Oliveira"
    assert fighter.nickname == "do Bronx"
    assert fighter.weight_class == "Lightweight"  # the "present" division, not the first one
    assert fighter.record == "37-11-0 (1 NC)"  # kickboxing wins ignored


def test_fighter_page_without_infobox() -> None:
    fighter = parse_fighter_page("<html><body>Stub</body></html>", "https://x/wiki/A")

    assert fighter.canonical_url == "https://x/wiki/A"
    assert (fighter.nickname, fighter.record, fighter.weight_class) == (None, None, None)
