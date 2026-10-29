"""Turn Wikipedia HTML into plain Python objects. No network or database access here."""

import datetime as dt
import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup, Tag

from app.models import CardPosition

WIKI_BASE = "https://en.wikipedia.org"
EVENT_LIST_URL = f"{WIKI_BASE}/wiki/List_of_UFC_events"


@dataclass
class FighterLink:
    """A fighter as they appear on a fight card."""

    name: str
    url: str  # Wikipedia article URL; used as the fighter's unique key
    has_page: bool  # False for "red links" (Wikipedia has no article for them yet)


@dataclass
class ParsedBout:
    """One row of a fight card."""

    weight_class: str | None
    left: FighterLink  # on finished fights Wikipedia lists the winner on the left
    right: FighterLink
    card_position: CardPosition
    outcome: str | None  # "left_won", "draw", "no_contest", or None if not fought yet
    method: str | None
    round: int | None


@dataclass
class ParsedEvent:
    """Everything read from one event page."""

    name: str
    date: dt.date
    location: str | None
    bouts: list[ParsedBout] = field(default_factory=list)


@dataclass
class ParsedFighter:
    """Extra details from a fighter's own Wikipedia page."""

    canonical_url: str
    nickname: str | None
    record: str | None
    weight_class: str | None


def clean_text(text: str) -> str:
    """Remove footnote markers like "[12]" and collapse whitespace."""
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return re.sub(r" ([,.])", r"\1", text).strip()  # "Nevada , USA" -> "Nevada, USA"


def parse_event_list(html: str, recent: int) -> tuple[list[str], list[str]]:
    """Return (upcoming event URLs, the `recent` most recent past event URLs)."""
    soup = BeautifulSoup(html, "html.parser")
    upcoming = _event_links_in_section(soup, "Scheduled_events")
    past = _event_links_in_section(soup, "Past_events")
    return upcoming, past[:recent]


def _event_links_in_section(soup: BeautifulSoup, heading_id: str) -> list[str]:
    heading = soup.find(id=heading_id)
    if heading is None:
        raise ValueError(f"Section {heading_id!r} not found on the events list page")
    table = heading.find_next("table")
    rows = table.find_all("tr")
    headers = [clean_text(c.get_text()) for c in rows[0].find_all(["th", "td"])]
    event_col = headers.index("Event")

    urls = []
    for row in rows[1:]:
        cells = row.find_all(["th", "td"])
        if len(cells) <= event_col:
            continue
        link = cells[event_col].find("a")
        # Skip events with no article yet (red links).
        if link and "new" not in link.get("class", []):
            urls.append(_absolute_url(link["href"]))
    return urls


def parse_event_page(html: str) -> ParsedEvent:
    """Parse an event article: name, date and location from the infobox, plus the fight card."""
    soup = BeautifulSoup(html, "html.parser")
    infobox = soup.select_one("table.infobox")
    if infobox is None:
        raise ValueError("Event page has no infobox")
    info = _infobox_fields(infobox)

    venue_and_city = [info[k] for k in ("Venue", "City") if info.get(k)]
    return ParsedEvent(
        name=_page_title(soup),
        date=_parse_infobox_date(infobox, info.get("Date", "")),
        location=", ".join(venue_and_city) or None,
        bouts=_parse_fight_card(soup),
    )


def _page_title(soup: BeautifulSoup) -> str:
    heading = soup.select_one("h1#firstHeading")
    if heading:
        return clean_text(heading.get_text())
    return clean_text(soup.title.get_text().removesuffix(" - Wikipedia"))


def _infobox_fields(infobox: Tag) -> dict[str, str]:
    fields = {}
    for row in infobox.find_all("tr"):
        label, value = row.find("th"), row.find("td")
        if label and value:
            fields.setdefault(clean_text(label.get_text()), clean_text(value.get_text(" ")))
    return fields


def _parse_infobox_date(infobox: Tag, date_text: str) -> dt.date:
    # Wikipedia hides an ISO date (e.g. 2024-12-07) inside the Date row; prefer that.
    iso = infobox.select_one("span.dtstart, span.bday")
    if iso:
        return dt.date.fromisoformat(iso.get_text(strip=True))
    match = re.search(r"[A-Z][a-z]+ \d{1,2}, \d{4}", date_text)
    if match:
        return dt.datetime.strptime(match.group(), "%B %d, %Y").date()
    raise ValueError(f"Could not read event date from {date_text!r}")


def _parse_fight_card(soup: BeautifulSoup) -> list[ParsedBout]:
    bouts = []
    main_card_count = 0
    in_prelims = False
    for table in soup.select("table.toccolours"):
        if "Weight class" not in table.get_text():
            continue  # some pages use the same styling for unrelated tables
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) == 1:
                # Section header row, e.g. "Main card" or "Preliminary card (ESPN2)".
                in_prelims = "prelim" in cells[0].get_text().lower()
                continue
            tds = row.find_all("td")
            if len(tds) < 6:
                continue  # column header row

            # The first two main-card fights are the main and co-main events.
            if in_prelims:
                position = CardPosition.PRELIM
            elif main_card_count == 0:
                position = CardPosition.MAIN
            elif main_card_count == 1:
                position = CardPosition.CO_MAIN
            else:
                position = CardPosition.MAIN_CARD
            if not in_prelims:
                main_card_count += 1

            bouts.append(_parse_bout_row(tds, position))
    return bouts


def _parse_bout_row(tds: list[Tag], position: CardPosition) -> ParsedBout:
    weight_class, left, verb, right, method_cell, round_cell = tds[:6]
    method = _clean_method(method_cell.get_text(" "))
    round_text = clean_text(round_cell.get_text())

    if clean_text(verb.get_text()) == "def.":
        outcome = "left_won"
    elif method and "draw" in method.lower():
        outcome = "draw"
    elif method and "no contest" in method.lower():
        outcome = "no_contest"
    else:
        outcome = None  # "vs." with no method: the fight hasn't happened yet

    return ParsedBout(
        weight_class=clean_text(weight_class.get_text()) or None,
        left=_fighter_link(left),
        right=_fighter_link(right),
        card_position=position,
        outcome=outcome,
        method=method,
        round=int(round_text) if round_text.isdigit() else None,
    )


def _clean_method(text: str) -> str | None:
    """ "Decision (unanimous) (29–28, 29–28, 30–27)" -> "Decision (unanimous)"."""
    text = clean_text(text)
    text = re.sub(r"\s*\([^)]*\d[^)]*\)", "", text)  # drop brackets containing scores
    return text[:100] or None


def _fighter_link(cell: Tag) -> FighterLink:
    link = cell.find("a")
    if link and "new" not in link.get("class", []) and "/wiki/" in link.get("href", ""):
        return FighterLink(
            name=clean_text(link.get_text()), url=_absolute_url(link["href"]), has_page=True
        )
    # No article: build the URL the article would have, so the fighter still has a stable key.
    name = link.get_text() if link else cell.get_text()
    name = re.sub(r"\((c|ic)\)", "", clean_text(name)).strip()  # drop champion markers
    return FighterLink(name=name, url=f"{WIKI_BASE}/wiki/{name.replace(' ', '_')}", has_page=False)


def _absolute_url(href: str) -> str:
    url = urljoin(WIKI_BASE, href).split("#")[0]
    return unquote(url)  # "%27" -> "'" so the same page always gets the same key


def parse_fighter_page(html: str, url: str) -> ParsedFighter:
    """Read nickname, division and MMA record from a fighter's infobox."""
    soup = BeautifulSoup(html, "html.parser")
    canonical = soup.select_one('link[rel="canonical"]')
    canonical_url = _absolute_url(canonical["href"]) if canonical else url

    infobox = soup.select_one("table.infobox")
    if infobox is None:
        return ParsedFighter(canonical_url, None, None, None)

    nicknames = _infobox_values(infobox, "Nickname") or _infobox_values(infobox, "Other names")
    nickname = nicknames[0] if nicknames else None

    # Fighters who changed weight list several divisions, e.g.
    # ["Featherweight (2013)", "Welterweight (2016–present)"]. Prefer the current one.
    divisions = _infobox_values(infobox, "Division")
    current = [d for d in divisions if "present" in d]
    division = (current or divisions or [None])[0]
    if division:
        division = division.split("(")[0].strip()

    return ParsedFighter(
        canonical_url=canonical_url,
        nickname=nickname[:120] if nickname else None,
        record=_mma_record(infobox),
        weight_class=division[:50] if division else None,
    )


def _infobox_values(infobox: Tag, label: str) -> list[str]:
    """All values in one infobox field. Some fields hold a list or several lines."""
    for row in infobox.find_all("tr"):
        th, td = row.find("th"), row.find("td")
        if th and td and clean_text(th.get_text()) == label:
            for style in td.find_all("style"):
                style.decompose()  # embedded CSS would otherwise show up as text
            items = td.find_all("li")
            if items:
                return [clean_text(li.get_text(" ")) for li in items]
            for br in td.find_all("br"):
                br.replace_with("\n")
            return [clean_text(line) for line in td.get_text().split("\n") if line.strip()]
    return []


def _mma_record(infobox: Tag) -> str | None:
    """Build "wins-losses-draws" from the infobox's "Mixed martial arts record" section."""
    counts: dict[str, int] = {}
    in_section = False
    for row in infobox.find_all("tr"):
        label, value = row.find("th"), row.find("td")
        label_text = clean_text(label.get_text()) if label else ""
        if label_text == "Mixed martial arts record":
            in_section = True
            continue
        if not in_section:
            continue
        if label and not value:
            break  # next section header: we're past the MMA record
        number = re.match(r"\d+", clean_text(value.get_text())) if value else None
        if label_text in ("Wins", "Losses", "Draws", "No contests") and number:
            counts[label_text] = int(number.group())

    if "Wins" not in counts:
        return None
    record = f"{counts['Wins']}-{counts.get('Losses', 0)}-{counts.get('Draws', 0)}"
    if counts.get("No contests"):
        record += f" ({counts['No contests']} NC)"
    return record
