# Car Rental System

A fully-featured car rental management system built as a portfolio project.
The goal is to demonstrate professional Python backend practices end-to-end:
schema design, a REST API, a simple web UI, automated email delivery, and a
CI pipeline — not just working code, but code that is structured, tested, and
maintainable.

---

## Contents

- [Architecture overview](#architecture-overview)
- [Database design](#database-design)
  - [Design decisions](#design-decisions)
  - [Normal forms](#normal-forms)
  - [The event log pattern](#the-event-log-pattern)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Running tests](#running-tests)
- [API reference](#api-reference)
- [Configuration](#configuration)
- [CI pipeline](#ci-pipeline)
- [Design trade-offs and known limitations](#design-trade-offs-and-known-limitations)

---

## Architecture overview

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI app                       │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │  /api/*  │  │  /ui/*   │  │  background tasks  │ │
│  │ (JSON)   │  │ (HTML)   │  │  (email dispatch)  │ │
│  └────┬─────┘  └────┬─────┘  └────────┬───────────┘ │
│       └─────────────┴────────────────┘              │
│                   services/                          │
│   rental_service  availability_service  notification │
└─────────────────────────┬───────────────────────────┘
                          │ SQLAlchemy ORM
                    MySQL 8.0+ database
```

The application is split into three horizontal layers:

- **API / UI layer** — FastAPI routers that handle HTTP concerns only (parsing, validation, response serialisation). They never contain business logic.
- **Service layer** — pure Python functions that implement the business rules (can this vehicle be rented? write the event, update the archive, dispatch the email). They are testable without an HTTP client.
- **Data layer** — SQLAlchemy models, Alembic migrations, and a session factory.

---

## Database design

### Design decisions

**Surrogate integer primary keys everywhere.**
Every table uses an `AUTO_INCREMENT INT` as its primary key. Natural keys (username, licence plate) are enforced as `UNIQUE` columns but are not PKs. This means renaming a user or correcting a vehicle's plate number does not cascade through every foreign key.

**Explicit `status` column on `vehicle`.**
A common mistake in rental systems is to imply vehicle availability by querying open reservations — a fragile and expensive approach. A `status` column with a `CHECK` constraint (`available`, `rented`, `maintenance`, `retired`) makes availability a single-column read and allows states that reservations cannot express.

**Soft deletes on `client` and `vehicle`.**
Hard-deleting a client or vehicle that appears in historical records would violate foreign key constraints or require cascading deletions that destroy history. An `is_deleted` flag and `deleted_at` timestamp allow "deletion" from the user's perspective while preserving referential integrity.

**The three-stage rental lifecycle.**
The system models three distinct moments that many systems incorrectly conflate:

| Stage | Table | Meaning |
|---|---|---|
| Intent | `reservation` | A future booking; optional (walk-ins skip this) |
| In progress | `active_rental` | Vehicle is currently out |
| Completed | `rental_archive` | Vehicle has been returned |

This separation means `reservation` is never modified to reflect what actually happened — it remains a pure statement of intent.

**Second driver as a foreign key.**
A simple boolean flag indicating a second driver exists tells you nothing about who that driver is — a gap with real legal implications. `active_rental.second_driver_id` points to a `client` row, making the second driver a first-class entity with their own identity documents on record.

**`created_at` / `updated_at` on every table.**
These timestamps cost nothing and are invaluable for debugging, auditing, API pagination, and cache invalidation. They are managed by MySQL's `DEFAULT CURRENT_TIMESTAMP` and `ON UPDATE CURRENT_TIMESTAMP`.

**Blacklist with a `date_end`.**
A blacklist entry without an expiry date means a client is banned permanently with no way to record that the ban was lifted. `date_end IS NULL` means permanent; a date value records when the ban was lifted.

### Normal forms

The operational tables (`user`, `client`, `vehicle`, `reservation`, `active_rental`, `rental_archive`) are in **Third Normal Form (3NF)**:

- **1NF**: every column is atomic (no comma-separated lists, no embedded JSON in operational tables).
- **2NF**: every non-key attribute depends on the whole primary key (all PKs are single-column surrogates, so partial dependency is impossible).
- **3NF**: every non-key attribute depends directly on the PK, not transitively through another non-key attribute.

`number_of_days` and `total` in `rental_archive` are `GENERATED ALWAYS AS` computed columns. They are technically derivable from `start_date`, `end_date`, and `price_per_day`, which would be a 3NF violation if stored redundantly. Because the database engine derives and maintains them automatically, inconsistency is impossible — this is accepted as a pragmatic exception.

### The event log pattern

`rental_event` intentionally violates 3NF. It contains a `payload` JSON column that duplicates data from `client` and `vehicle`. This is correct design for an **immutable log**:

> Normalisation guards against update anomalies (inserting, modifying, or deleting data inconsistently). Update anomalies cannot occur on a table that is never updated. The purpose of `rental_event` is different from the purpose of an operational table — it records what was true at a specific past moment, not what is true now. Normalising it would destroy its core property: historical accuracy independent of future data changes.

The `rental_archive` table sits alongside `rental_event`. It is fully normalised and serves day-to-day queries via JOINs with current `client` and `vehicle` data. For historical accuracy (e.g. generating an invoice for a rental from two years ago), the application reads from `rental_event.payload` instead.

**Why JSON in the event payload rather than 30 `snap_` columns?**
A `snap_` column approach requires a schema migration every time a column is added to `client` or `vehicle`. With JSON, adding `client.middle_name` tomorrow means future events automatically include it — old events remain valid as-is without any migration. The trade-off is that reporting on payload fields requires JSON path expressions rather than simple column references; the `v_invoice` view abstracts this away.

---

## Project structure

```
car-rental/
├── .env.example            # configuration template — copy to .env
├── .gitignore
├── .sqlfluff               # SQL formatter config
├── alembic.ini             # Alembic config — URL overridden by env.py
├── pyproject.toml          # all tool config: black, ruff, pytest, mypy
├── README.md
├── CONTRIBUTING.md         # conventional commits and development workflow
│
├── scripts/
│   └── init_repo.sh        # one-time script to create the git commit history
│
├── db/
│   ├── migrations/         # Alembic migration scripts
│   │   ├── env.py          # wires SQLAlchemy metadata into Alembic
│   │   ├── script.py.mako  # template for generated migration files
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── seeds/              # Faker-based test data
│   │   ├── factories.py    # factory functions — used by seed.py AND tests
│   │   └── seed.py         # CLI entry point: python db/seeds/seed.py
│   └── sql/
│       └── schema.sql      # human-readable reference DDL
│
├── app/
│   ├── config.py           # typed Settings loaded from .env
│   ├── database.py         # SQLAlchemy engine + session factory + Base
│   ├── models/             # ORM models — one file per table
│   │   ├── __init__.py     # re-exports all models; Alembic discovers them here
│   │   ├── mixins.py       # TimestampMixin (created_at / updated_at)
│   │   ├── user.py
│   │   ├── client.py
│   │   ├── vehicle.py
│   │   ├── reservation.py
│   │   ├── active_rental.py
│   │   ├── rental_event.py  # immutable event log — no TimestampMixin
│   │   ├── rental_archive.py
│   │   ├── blacklist.py
│   │   └── notification.py
│   ├── schemas/            # Pydantic request/response models
│   │   └── .gitkeep        # placeholder — removed when first schema is added
│   ├── api/                # FastAPI routers
│   │   └── .gitkeep        # placeholder — removed when first router is added
│   ├── services/           # business logic (decoupled from HTTP)
│   │   └── .gitkeep        # placeholder — removed when first service is added
│   └── ui/                 # Jinja2 templates + static files
│       ├── templates/
│       │   ├── .gitkeep    # placeholder — removed when first template is added
│       │   ├── base.html   # HTML skeleton extended by all pages
│       │   ├── vehicles.html
│       │   ├── clients.html
│       │   └── rentals.html
│       └── static/
│           ├── .gitkeep    # placeholder — removed when first asset is added
│           └── style.css
│
├── tests/
│   ├── conftest.py              # shared fixtures and persisted model fixtures
│   ├── unit/                    # pure Python — no database required
│   │   ├── test_models.py       # model properties: full_name, is_available, total…
│   │   └── test_factories.py    # factory output: correct keys, types, constraints
│   └── integration/             # SQLite in-memory — real DB writes and reads
│       └── test_db_models.py    # persistence, relationships, integrity errors
│
└── .github/
    └── workflows/
        └── ci.yml          # lint → format → test → coverage
```

---

## Getting started

### Prerequisites

- Python 3.11+
- MySQL 8.0+ running locally (or via Docker)
- A [Resend](https://resend.com) account for email (free tier: 3 000 emails/month)
- Git with a configured identity (required before the first commit)

### First-time git setup

If you have never configured git on this machine, do this once before
running `scripts/init_repo.sh`:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

You can verify it is set with:

```bash
git config --global user.name
git config --global user.email
```

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/car-rental.git
cd car-rental

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install all dependencies (including dev tools)
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and API keys

# Create the database
mysql -u root -p -e "CREATE DATABASE car_rental CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE USER 'car_rental_user'@'localhost' IDENTIFIED BY 'your_password';"
mysql -u root -p -e "GRANT ALL ON car_rental.* TO 'car_rental_user'@'localhost';"

# Run migrations
alembic upgrade head

# (Optional) Seed with fake data
python db/seeds/seed.py

# Start the development server
uvicorn app.api.main:app --reload
```

The application will be available at `http://localhost:8000`.
Interactive API docs are at `http://localhost:8000/docs`.

---

## Running tests

```bash
# All tests with coverage report
pytest

# Unit tests only (no database required)
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# With verbose output
pytest -v
```

Coverage must stay above 80% (enforced in CI).

---

## API reference

Full interactive documentation is available at `/docs` (Swagger UI) and `/redoc` when the server is running.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/vehicles` | List vehicles, filterable by status and dates |
| `GET` | `/api/vehicles/{id}` | Get a single vehicle |
| `POST` | `/api/vehicles` | Add a vehicle to the fleet |
| `GET` | `/api/clients` | List clients |
| `POST` | `/api/clients` | Register a new client |
| `GET` | `/api/rentals/available` | Available vehicles for a date range |
| `POST` | `/api/rentals` | Open a new rental |
| `POST` | `/api/rentals/{id}/close` | Close a rental and trigger invoice email |
| `GET` | `/api/rentals/{id}/invoice` | Retrieve historical invoice from event log |

---

## Configuration

All configuration is via environment variables. See `.env.example` for the full list with descriptions. Key settings:

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `APP_ENV` | `development` | `development` or `production` |
| `APP_SECRET_KEY` | — | Session signing key; generate with `openssl rand -hex 32` |
| `RESEND_API_KEY` | — | Email delivery API key |
| `DEFAULT_CURRENCY` | `EUR` | Currency for all monetary values |
| `DEFAULT_COUNTRY` | `France` | Default country for domestic addresses |

---

## CI pipeline

GitHub Actions runs on every push and pull request:

1. **Lint** — `ruff check .`
2. **Format check** — `black --check .`
3. **SQL format check** — `sqlfluff lint db/sql/`
4. **Type check** — `mypy app/`
5. **Tests** — `pytest` with SQLite in-memory (no MySQL required in CI)
6. **Coverage gate** — fails if coverage drops below 80%

---

## Design trade-offs and known limitations

**SQLite in CI vs MySQL in production.**
Integration tests use SQLite in-memory for speed and zero infrastructure. This means MySQL-specific features (JSON path operators in views, `GENERATED ALWAYS AS STORED`) are not exercised in CI. The `v_invoice` view is tested indirectly via the service layer, which reconstructs invoice data from the JSON payload in Python rather than in SQL.

**Single-currency.**
All monetary values are in EUR. Multi-currency support would require a `currency` column on `rental_archive` and `rental_event`, and an exchange rate table. This is out of scope for a portfolio project.

**No authentication middleware yet.**
The `user` table and `role` column exist, but the API endpoints are currently unprotected. JWT-based authentication via `fastapi-users` or a custom middleware is the natural next step.

**Email is best-effort.**
The `notification` table records the outcome of every send attempt (sent, failed, bounced). There is no automatic retry on failure. A production system would add a retry queue (Celery + Redis, or simply a scheduled task that re-processes `status = 'failed'` rows).
