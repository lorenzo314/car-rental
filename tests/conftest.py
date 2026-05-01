"""
Shared pytest fixtures.

Database strategy
-----------------
Tests use SQLite in-memory rather than MySQL.  SQLAlchemy abstracts the
difference for all operations used in tests.  The two MySQL-specific
features in the production schema (GENERATED ALWAYS AS, JSON path
operators in views) are handled in Python instead:

  - number_of_days and total are Python properties on RentalArchive.
  - Invoice data is reconstructed from the payload dict in Python,
    not via SQL views.

Each test gets a fresh database: the schema is created from Base.metadata
at the start of the session and each test runs in a transaction that is
rolled back afterwards.  This is fast and keeps tests fully isolated.

Fixtures
--------
db          Scoped to each test.  A SQLAlchemy Session backed by SQLite
            in-memory.  Rolls back after each test.

agent       A persisted User with role="agent".
admin       A persisted User with role="admin".
client      A persisted Client with email_consent=True.
vehicle     A persisted Vehicle with status="available".
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import (  # noqa: F401 — registers all models on Base.metadata
    ActiveRental,
    Blacklist,
    Client,
    Notification,
    RentalArchive,
    RentalEvent,
    Reservation,
    User,
    Vehicle,
)
from db.seeds.factories import (
    active_rental_factory,
    client_factory,
    rental_event_payload,
    user_factory,
    vehicle_factory,
)

# ---------------------------------------------------------------------------
# Engine — shared across the entire test session
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """Create the SQLite in-memory engine and schema once per session."""
    _engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)
    _engine.dispose()


# ---------------------------------------------------------------------------
# Database session — fresh transaction per test, rolled back after
# ---------------------------------------------------------------------------

@pytest.fixture
def db(engine) -> Session:
    """Yield a session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestSession()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Persisted model fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def agent(db: Session) -> User:
    user = User(**user_factory(username="test_agent", role="agent"))
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def admin(db: Session) -> User:
    user = User(**user_factory(username="test_admin", role="admin"))
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def client(db: Session) -> Client:
    data = client_factory()
    data["email_consent"] = True
    data["email"] = "test.client@example.com"
    c = Client(**data)
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def second_driver(db: Session) -> Client:
    """A second client to act as second driver in rental tests."""
    data = client_factory()
    data["email"] = "second.driver@example.com"
    c = Client(**data)
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def vehicle(db: Session) -> Vehicle:
    v = Vehicle(**vehicle_factory(status="available"))
    db.add(v)
    db.flush()
    return v


@pytest.fixture
def rented_vehicle(db: Session) -> Vehicle:
    v = Vehicle(**vehicle_factory(status="rented"))
    db.add(v)
    db.flush()
    return v


@pytest.fixture
def active_rental(db: Session, vehicle: Vehicle, client: Client, agent: User) -> ActiveRental:
    """An open rental linking the vehicle, client, and agent fixtures."""
    rental = ActiveRental(
        **active_rental_factory(
            vehicle_id=vehicle.id,
            client_id=client.id,
            opened_by=agent.id,
        )
    )
    vehicle.status = "rented"
    db.add(rental)
    db.flush()
    return rental


@pytest.fixture
def rental_archive(
    db: Session,
    vehicle: Vehicle,
    client: Client,
    agent: User,
) -> RentalArchive:
    """A completed rental with its associated event."""
    from datetime import date, timedelta

    start = date.today() - timedelta(days=5)
    end = date.today() - timedelta(days=1)
    price = 45.00

    payload = rental_event_payload(
        vehicle={
            "id": vehicle.id,
            "brand": vehicle.brand,
            "licence_plate": vehicle.licence_plate,
            "colour": vehicle.colour,
            "fuel_type": vehicle.fuel_type,
            "spare_wheel": vehicle.spare_wheel,
            "fuel_level": vehicle.fuel_level,
            "automatic": vehicle.automatic,
            "price_per_day": price,
        },
        client={
            "id": client.id,
            "last_name": client.last_name,
            "first_name": client.first_name,
            "nationality": client.nationality,
            "national_id": client.national_id,
            "licence_number": client.licence_number,
            "email": client.email,
            "address_line": client.address_line,
            "city": client.city,
            "postal_code": client.postal_code,
            "country": client.country,
            "phone": client.phone,
        },
        start_date=start,
        end_date=end,
        price_per_day=price,
        agent_username=agent.username,
    )

    event = RentalEvent(
        event_type="rental_closed",
        recorded_by=agent.id,
        vehicle_id=vehicle.id,
        client_id=client.id,
        payload=payload,
    )
    db.add(event)
    db.flush()

    archive = RentalArchive(
        event_id=event.id,
        vehicle_id=vehicle.id,
        client_id=client.id,
        closed_by=agent.id,
        start_date=start,
        end_date=end,
        price_per_day=price,
    )
    db.add(archive)
    db.flush()
    return archive
