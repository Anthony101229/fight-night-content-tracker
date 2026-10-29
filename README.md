# Fight Night Content Tracker

[![CI](https://github.com/Anthony101229/fight-night-content-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/Anthony101229/fight-night-content-tracker/actions/workflows/ci.yml)

An internal tool a sports-media Content Operations team could use to plan and track
video coverage of MMA events. It scrapes upcoming and recent UFC events with their fight
cards, lets the team assign a camera crew to each event, and tracks each bout's footage
from **planned → shot → edited → delivered**.

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · PostgreSQL 16 ·
httpx + BeautifulSoup · React + TypeScript (Vite) · Recharts · Docker Compose · GitHub Actions

## Screenshots

<!-- TODO: add screenshots after moving some bouts past "planned" so the chart shows progress. -->

| Events and footage chart | Event detail |
|---|---|
| ![Events list with footage status chart](docs/screenshots/events.png) | ![Event detail with fight card and crew](docs/screenshots/event-detail.png) |

## Features

- **Scraper.** Pulls upcoming and recent events, fight cards and fighters from Wikipedia.
  It waits 1 second between requests, caches raw HTML on disk, and is **idempotent**:
  re-running updates existing rows instead of creating duplicates.
- **REST API.** List and filter events, get an event with its full card, assign or
  unassign crew, update footage status per bout, and get a delivered-vs-pending summary
  per event. Interactive docs are at `/docs`.
- **Dashboard.** An events list with upcoming/past filters, search, and a chart of footage
  status per event. The event page shows the fight card with a status dropdown per bout
  and crew assignment.
- **Tests and CI.** A pytest suite runs against a real Postgres, with each test rolled back
  afterwards. GitHub Actions runs lint, tests, a frontend build and the Docker builds on
  every push and pull request.

## Architecture

```mermaid
flowchart LR
    team((Content Ops team)) --> web

    subgraph compose [docker compose]
        web["web<br/>React + TypeScript<br/>(Vite dev server)"]
        subgraph api_box [api · Python 3.12]
            api["FastAPI<br/>REST API"]
            scraper["Scraper CLI<br/>httpx + BeautifulSoup"]
        end
        db[("db<br/>PostgreSQL 16")]
    end

    wiki["Wikipedia<br/>/wiki/ article pages"]

    web -- "/api/* (proxied)" --> api
    api -- "SQLAlchemy 2.0" --> db
    scraper -- "upsert by natural key" --> db
    wiki -- "rate-limited, cached HTML" --> scraper
```

### Data model

```mermaid
erDiagram
    EVENT ||--o{ BOUT : "has on its card"
    EVENT ||--o{ CREW_ASSIGNMENT : staffs
    CREW_MEMBER ||--o{ CREW_ASSIGNMENT : "works"
    FIGHTER ||--o{ BOUT : "red corner"
    FIGHTER ||--o{ BOUT : "blue corner"
    BOUT ||--|| FOOTAGE_ASSET : "has one"

    EVENT {
        int id PK
        string name
        date date
        string location
        string source_url UK
    }
    FIGHTER {
        int id PK
        string name
        string nickname
        string record
        string weight_class
        string source_url UK
    }
    BOUT {
        int id PK
        int event_id FK
        int red_fighter_id FK
        int blue_fighter_id FK
        enum card_position
        string result
        string method
        int round
    }
    CREW_MEMBER {
        int id PK
        string name
        enum role
    }
    CREW_ASSIGNMENT {
        int id PK
        int event_id FK
        int crew_member_id FK
        enum role
    }
    FOOTAGE_ASSET {
        int id PK
        int bout_id FK, UK
        enum status
        text notes
        timestamptz updated_at
    }
```

Deleting an event deletes its bouts, footage records and crew assignments. Fighters and
crew members are kept, because they belong to many events.

## Quick start

Requires Docker Desktop.

```bash
cp .env.example .env              # then set SCRAPER_CONTACT to your email or a URL
docker compose up --build -d      # starts db, api (runs migrations on start) and web
docker compose exec api python -m app.seed      # add demo crew members
docker compose exec api python -m app.scraper   # scrape events (a few minutes the first time)
```

Then open:

- Dashboard: <http://localhost:5173>
- API docs: <http://localhost:8000/docs>

Run the scraper again any time. Pages fetched in the last 24 hours come from the cache,
and existing rows are updated rather than duplicated. Use `--recent N` to choose how many
past events to include (default 10). All scheduled events are always included.

## Environment variables

Set these in `.env` (copied from [`.env.example`](.env.example)). `.env` is gitignored.

| Variable | Used by | Default | Purpose |
|---|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | db, api | `fightnight` | Database credentials for the compose stack |
| `DATABASE_URL` | api, scraper, tests | `postgresql+psycopg://fightnight:fightnight@localhost:5433/fightnight` | Used when running Python outside Docker. Inside compose, the api service gets a URL that points at the `db` host |
| `SCRAPER_CONTACT` | scraper | none (**required**) | Email or URL included in the User-Agent, as Wikipedia's bot policy requires |
| `SCRAPER_DELAY_SECONDS` | scraper | `1.0` | Minimum gap between real HTTP requests |
| `SCRAPER_CACHE_HOURS` | scraper | `24` | Re-download a page once its cached copy is older than this |
| `SCRAPER_CACHE_DIR` | scraper | `data/cache` | Where raw HTML is cached (gitignored) |
| `TEST_DATABASE_URL` | tests | `DATABASE_URL` with `_test` appended to the database name | Test database; created and migrated automatically |
| `API_PROXY_TARGET` | web | `http://localhost:8000` | Where Vite forwards `/api/*` requests |

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/events` | List events, newest first. Filters: `when=upcoming\|past`, `q`, `date_from`, `date_to`, `limit`, `offset` |
| `GET` | `/events/{id}` | One event with its fight card (fighters + footage) and crew |
| `POST` | `/events/{id}/crew` | Assign crew: `{"crew_member_id": 1, "role": "producer"}` (`role` is optional) |
| `DELETE` | `/events/{id}/crew/{crew_member_id}` | Unassign crew |
| `PATCH` | `/bouts/{id}/footage` | Partial update: `{"status": "shot", "notes": "..."}` |
| `GET` | `/footage/summary` | Per event: total bouts, count per status, and pending. Same filters as `/events` |
| `GET` | `/crew-members` | All crew members |
| `GET` | `/health` | Liveness check |

## Development

```bash
# Tests (inside the api container)
docker compose exec api pytest
docker compose exec api pytest --cov=app --cov-report=term-missing

# Lint and format
docker compose exec api ruff check .
docker compose exec api ruff format .

# Frontend type check + production build
cd frontend && npm ci && npm run build

# New migration after changing app/models.py (always review the generated file)
docker compose exec api alembic revision --autogenerate -m "describe the change"
docker compose exec api alembic upgrade head
```

The tests use a separate `<db>_test` database. They build its schema by running the real
migrations (down, then up) and roll back each test's transaction, so they never touch your
data and can run in any order.

## Project structure

```
backend/
  app/
    main.py            FastAPI app
    models.py          SQLAlchemy models
    schemas.py         Pydantic request/response models
    routers/           events, crew, footage endpoints
    scraper/           fetcher (HTTP + cache), parsers (HTML), loader (DB upserts), CLI
    seed.py            demo crew members
  alembic/versions/    migrations
  tests/               pytest suite
frontend/
  src/pages/           Events list and Event detail pages
  src/components/      Footage chart
  src/api.ts           typed API client
.github/workflows/     CI
docker-compose.yml
```

## Design notes

- **Idempotent scraping.** Every row has a natural key: the Wikipedia URL for events and
  fighters, and (event + both fighters) for bouts. The loader looks each one up before
  creating it, and database unique constraints back that up. Bouts match the two fighters
  in **either order**, because once a fight happens Wikipedia moves the winner to the left.
  Fighters are keyed by the canonical URL, so redirects don't create duplicates.
- **The scraper never overwrites the team's work.** It updates facts (names, dates,
  results). Footage status and crew assignments belong to the team.
- **Polite scraping.** One request per second, a 24-hour HTML cache, `Retry-After`
  handling on HTTP 429, and a descriptive User-Agent with contact info.
- **Avoiding N+1 queries.** The event detail endpoint uses `selectinload`, so a card of any
  size loads in a fixed number of queries.
- **No CORS needed.** The Vite dev server proxies `/api` to FastAPI, so the browser only
  ever talks to one site.

## Data source and attribution

Event, fight card and fighter data come from
[Wikipedia](https://en.wikipedia.org/wiki/List_of_UFC_events) and are available under the
[Creative Commons Attribution-ShareAlike 4.0 License](https://creativecommons.org/licenses/by-sa/4.0/).
The scraper only requests `/wiki/` article pages, which robots.txt allows, and follows the
[Wikimedia robot policy](https://wikitech.wikimedia.org/wiki/Robot_policy).

The original plan used UFCStats. As of October 2026 every UFCStats page sits behind a
JavaScript "checking your browser" challenge meant to block automated clients, so this
project does not scrape it.

## Measured results

From the first full scrape on 2026-10-28 (9 upcoming + 10 recent events):

| Metric | Value |
|---|---|
| Events / bouts / fighters scraped | 19 / 181 / 352 |
| HTTP requests | 238 |
| Full scrape time | 249.8 s (rate limit: 1 request/s) |
| Backend tests | 40, all passing in ~1.5 s |
| Line coverage (`pytest --cov=app`) | 84% (the uncovered code is the scraper CLI and the seed script) |

## Known limitations and roadmap

- **Google Sheets sync** (push an event's schedule, crew and footage status to a Sheet):
  planned, not yet built.
- A bout cancelled after it was scraped stays in the database. Deleting it automatically
  could also delete the team's footage notes.
- Fighters without a Wikipedia article have a name and weight class, but no record or
  nickname.
- No authentication. This is meant as an internal tool on a trusted network.
