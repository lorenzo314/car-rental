#!/usr/bin/env bash
# =============================================================================
# init_repo.sh
#
# Initialises the git repository with a clean conventional commit history.
# Run ONCE from the project root after cloning or creating the repo.
#
# Usage:
#   chmod +x scripts/init_repo.sh
#   ./scripts/init_repo.sh
#
# What it does:
#   1. Initialises git if not already done
#   2. Creates the initial commit sequence, one commit per logical layer
#   3. Each commit message follows the Conventional Commits specification
#
# After running this script, push to GitHub:
#   git remote add origin https://github.com/youruser/car-rental.git
#   git push -u origin main
# =============================================================================

set -euo pipefail

echo "Initialising car-rental repository..."

# ---------------------------------------------------------------------------
# 1. Git init
# ---------------------------------------------------------------------------
if [ ! -d ".git" ]; then
  git init
  git checkout -b main
  echo "  git init done"
else
  echo "  git already initialised — skipping init"
fi

# ---------------------------------------------------------------------------
# 2. Configure git identity if not already set
# ---------------------------------------------------------------------------
if [ -z "$(git config user.email)" ]; then
  echo "  Git identity not set. Please run:"
  echo "    git config --global user.name 'Your Name'"
  echo "    git config --global user.email 'you@example.com'"
  exit 1
fi

# ---------------------------------------------------------------------------
# 3. Commit sequence
# Each commit is one logical layer.  This gives a clean, readable history
# that a reviewer can follow from the ground up.
# ---------------------------------------------------------------------------

# -- Commit 1: project scaffold ----------------------------------------------
git add \
  .gitignore \
  .env.example \
  pyproject.toml \
  .sqlfluff \
  README.md \
  CONTRIBUTING.md \
  scripts/init_repo.sh

git commit -m "chore: initial project scaffold

Adds project configuration files:
- pyproject.toml with black, ruff, mypy, pytest config
- .sqlfluff for SQL formatting conventions
- .gitignore
- .env.example with all required variables documented
- README.md with architecture overview and design decisions
- CONTRIBUTING.md with conventional commit guide"

# -- Commit 2: database schema -----------------------------------------------
git add db/sql/schema.sql alembic.ini db/migrations/script.py.mako

git commit -m "db(schema): add reference DDL for MySQL 8.0

Full schema with 9 tables:
user, client, vehicle, reservation, active_rental,
rental_event (immutable event log), rental_archive,
blacklist, notification.

Design highlights:
- Surrogate integer PKs throughout
- Explicit vehicle.status column
- Soft deletes on client and vehicle
- second_driver_id FK on active_rental
- rental_event stores immutable JSON snapshot
- created_at / updated_at on all mutable tables
- All monetary values in EUR"

# -- Commit 3: Alembic migration ---------------------------------------------
git add db/migrations/

git commit -m "db(migrations): add initial Alembic migration

0001_initial_schema.py creates all tables and indexes
in the correct dependency order.  downgrade() drops them
in reverse order.

env.py wires Base.metadata from app.models so that
alembic revision --autogenerate detects future changes."

# -- Commit 4: application config and database layer -------------------------
git add app/__init__.py app/config.py app/database.py db/__init__.py

git commit -m "chore(config): add typed settings and database session factory

app/config.py
- Pydantic Settings class loaded from .env
- db_url and db_url_async as computed fields
- lru_cache singleton — .env read once per process
- is_production helper property

app/database.py
- SQLAlchemy engine with pool_pre_ping and pool_recycle
- SessionLocal factory
- get_db() FastAPI dependency with guaranteed cleanup
- Shared Base for all ORM models"

# -- Commit 5: ORM models + empty package placeholders ----------------------
git add app/models/
git add \
  app/schemas/.gitkeep \
  app/api/.gitkeep \
  app/services/.gitkeep \
  app/ui/templates/.gitkeep \
  app/ui/static/.gitkeep

git commit -m "feat(models): add SQLAlchemy ORM models for all tables

One file per table, all using mapped_column() and
Mapped[] type annotations (SQLAlchemy 2.0 style).

mixins.py       TimestampMixin — created_at / updated_at
user.py         staff accounts with surrogate PK
client.py       renters with soft delete and full_name property
vehicle.py      fleet with explicit status and is_available property
reservation.py  optional pre-booking with number_of_days / total properties
active_rental.py open rentals with second_driver_id FK
rental_event.py  immutable log — no TimestampMixin, soft FK references
rental_archive.py closed rentals with number_of_days / total as properties
blacklist.py    refused clients with optional date_end
notification.py  outbound email audit trail

__init__.py re-exports all models so Alembic autogenerate
discovers them via a single import.

.gitkeep files added to reserve empty directories:
app/schemas/ app/api/ app/services/
app/ui/templates/ app/ui/static/"

# -- Commit 6: seeds and factories -------------------------------------------
git add db/seeds/

git commit -m "feat(seeds): add Faker-based factories and seed script

db/seeds/factories.py
- One factory function per table returning plain dicts
- rental_event_payload() is the single source of truth
  for the JSON snapshot structure — used by seeds AND tests
- Faker locale: fr_FR for realistic French names / addresses
- Faker.seed(42) for reproducible output

db/seeds/seed.py
- Idempotent: clears all data before seeding
- Creates fixed users alice (admin) and bob (agent)
- Accepts CLI args: --clients --vehicles --rentals
- Creates past rentals with events, archives, notifications"

# -- Commit 7: tests ---------------------------------------------------------
git add tests/

git commit -m "test: add unit and integration test suites

tests/conftest.py
- SQLite in-memory engine, schema created once per session
- Per-test transaction rollback for full isolation
- Fixtures: agent, admin, client, second_driver, vehicle,
  active_rental, rental_archive

tests/unit/test_models.py
- Model property tests (no DB): full_name, is_available,
  number_of_days, total, repr

tests/unit/test_factories.py
- Factory output validation: keys, types, constraints,
  payload structure, date arithmetic

tests/integration/test_db_models.py
- Persistence, relationship loading, UniqueConstraint
  and IntegrityError verification against SQLite"

# -- Commit 8: CI ------------------------------------------------------------
git add .github/

git commit -m "ci: add GitHub Actions workflow

.github/workflows/ci.yml runs on push and pull_request
to main and develop branches.

Steps:
1. ruff check      (lint)
2. black --check   (format)
3. sqlfluff lint   (SQL format)
4. mypy app/       (type check)
5. pytest          (tests + coverage gate 80%)
6. Upload htmlcov/ as a workflow artifact (7-day retention)

Tests use SQLite in-memory — no MySQL service container
required in CI."

echo ""
echo "Repository initialised with $(git log --oneline | wc -l) commits."
echo ""
echo "Next steps:"
echo "  git remote add origin https://github.com/youruser/car-rental.git"
echo "  git push -u origin main"
