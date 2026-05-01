"""
Faker-based factory functions for generating realistic test data.

Each factory function returns a plain dict of column values ready to be
passed to the corresponding SQLAlchemy model constructor.  They do NOT
write to the database — that is the seed script's responsibility.

This separation means the same factories can be used in pytest fixtures
without any database interaction:

    from db.seeds.factories import user_factory, client_factory

    def test_something():
        data = client_factory()
        client = Client(**data)
        ...

Design notes
------------
- All monetary values are in EUR.
- Default country is France; foreign addresses use a different country.
- Passwords are pre-hashed with bcrypt.  The plaintext for all seeded
  users is "password123" — never use this in production.
- Dates are kept realistic: date_of_birth between 1950 and 2000,
  licence/passport issued within the last 10 years, rentals in the
  recent past.
"""

import random
from datetime import date, timedelta

from faker import Faker

fake = Faker("fr_FR")  # French locale for realistic names and addresses
Faker.seed(42)  # reproducible output across runs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _past_date(years_ago_min: int = 1, years_ago_max: int = 5) -> date:
    today = date.today()
    start = today - timedelta(days=years_ago_max * 365)
    end = today - timedelta(days=years_ago_min * 365)
    return _random_date(start, end)


def _future_date(days_min: int = 1, days_max: int = 30) -> date:
    today = date.today()
    return today + timedelta(days=random.randint(days_min, days_max))


# ---------------------------------------------------------------------------
# user
# ---------------------------------------------------------------------------


def user_factory(
    *,
    username: str | None = None,
    role: str = "agent",
    is_active: bool = True,
) -> dict:
    """Return a dict suitable for constructing a User.

    The password hash corresponds to the plaintext "password123".
    Generated with: bcrypt.hashpw(b"password123", bcrypt.gensalt())
    """
    return {
        "username": username or fake.user_name(),
        # bcrypt hash of "password123" — safe for dev/test use only
        "password_hash": (
            "$2b$12$KIXHs3JUGMmMGKTqxne9DOSMxjDqO4dLsLFnJCu/B.4t8R6wWtNYi"
        ),
        "role": role,
        "is_active": is_active,
    }


def admin_factory(*, username: str | None = None) -> dict:
    return user_factory(username=username, role="admin")


# ---------------------------------------------------------------------------
# client
# ---------------------------------------------------------------------------

FRENCH_CITIES = ["Paris", "Lyon", "Marseille", "Bordeaux", "Nantes", "Toulouse"]
FOREIGN_COUNTRIES = ["Germany", "Spain", "Italy", "United Kingdom", "Belgium"]


def client_factory(*, is_deleted: bool = False) -> dict:
    dob = _random_date(date(1950, 1, 1), date(2000, 12, 31))
    licence_date = _past_date(1, 10)
    passport_date = _past_date(1, 9)
    has_foreign = random.random() > 0.5

    return {
        "last_name": fake.last_name().upper(),
        "first_name": fake.first_name(),
        "date_of_birth": dob,
        "nationality": random.choice(
            ["French", "German", "Spanish", "British", "Italian"]
        ),
        "national_id": fake.bothify("??######").upper(),
        "licence_number": fake.bothify("??######??").upper(),
        "licence_issued_on": licence_date,
        "passport_number": fake.bothify("??#######").upper(),
        "passport_issued_on": passport_date,
        # Domestic address
        "address_line": fake.street_address(),
        "city": random.choice(FRENCH_CITIES),
        "postal_code": fake.postcode(),
        "country": "France",
        "phone": fake.phone_number(),
        # Foreign address (optional)
        "foreign_address_line": fake.street_address() if has_foreign else None,
        "foreign_city": fake.city() if has_foreign else None,
        "foreign_country": random.choice(FOREIGN_COUNTRIES) if has_foreign else None,
        "foreign_phone": fake.phone_number() if has_foreign else None,
        # Contact
        "email": fake.email(),
        "email_consent": random.choice([True, False]),
        "has_second_driver": random.random() > 0.7,
        "photo_url": None,
        # Soft delete
        "is_deleted": is_deleted,
        "deleted_at": date.today() if is_deleted else None,
    }


# ---------------------------------------------------------------------------
# vehicle
# ---------------------------------------------------------------------------

VEHICLE_BRANDS = [
    "Renault Clio",
    "Peugeot 208",
    "Citroën C3",
    "Renault Megane",
    "Peugeot 308",
    "Volkswagen Golf",
    "Toyota Yaris",
    "Ford Focus",
    "Opel Corsa",
    "Dacia Sandero",
]

COLOURS = ["white", "black", "grey", "blue", "red", "silver", "green"]
FUEL_TYPES = ["petrol", "diesel", "electric", "hybrid"]
STATUSES = ["available", "rented", "maintenance"]


def vehicle_factory(
    *,
    status: str | None = None,
    is_deleted: bool = False,
) -> dict:
    return {
        "brand": random.choice(VEHICLE_BRANDS),
        "licence_plate": fake.bothify("??-###-??").upper(),
        "colour": random.choice(COLOURS),
        "fuel_type": random.choice(FUEL_TYPES),
        "spare_wheel": random.choice([True, False]),
        "fuel_level": random.randint(10, 100),
        "automatic": random.random() > 0.5,
        "status": status or random.choice(STATUSES),
        "price_per_day": round(random.uniform(25.0, 120.0), 2),
        "photo_url": None,
        "is_deleted": is_deleted,
        "deleted_at": date.today() if is_deleted else None,
    }


def available_vehicle_factory() -> dict:
    return vehicle_factory(status="available")


def rented_vehicle_factory() -> dict:
    return vehicle_factory(status="rented")


# ---------------------------------------------------------------------------
# reservation
# ---------------------------------------------------------------------------


def reservation_factory(
    *,
    vehicle_id: int,
    client_id: int,
    created_by: int,
    start_date: date | None = None,
    end_date: date | None = None,
    price_per_day: float | None = None,
) -> dict:
    start = start_date or _future_date(days_min=1, days_max=14)
    end = end_date or (start + timedelta(days=random.randint(1, 7)))
    return {
        "start_date": start,
        "end_date": end,
        "price_per_day": price_per_day or round(random.uniform(25.0, 120.0), 2),
        "vehicle_id": vehicle_id,
        "client_id": client_id,
        "created_by": created_by,
    }


# ---------------------------------------------------------------------------
# active_rental
# ---------------------------------------------------------------------------


def active_rental_factory(
    *,
    vehicle_id: int,
    client_id: int,
    opened_by: int,
    reservation_id: int | None = None,
    second_driver_id: int | None = None,
    start_date: date | None = None,
    expected_end_date: date | None = None,
    price_per_day: float | None = None,
    status: str = "active",
) -> dict:
    start = start_date or _past_date(years_ago_min=0, years_ago_max=1)
    # Clamp start to at most 30 days ago
    today = date.today()
    if start > today:
        start = today - timedelta(days=random.randint(1, 7))
    end = expected_end_date or (start + timedelta(days=random.randint(1, 7)))
    return {
        "reservation_id": reservation_id,
        "vehicle_id": vehicle_id,
        "client_id": client_id,
        "second_driver_id": second_driver_id,
        "opened_by": opened_by,
        "start_date": start,
        "expected_end_date": end,
        "price_per_day": price_per_day or round(random.uniform(25.0, 120.0), 2),
        "status": status,
    }


# ---------------------------------------------------------------------------
# rental_event payload
# ---------------------------------------------------------------------------


def rental_event_payload(
    *,
    vehicle: dict,
    client: dict,
    start_date: date,
    end_date: date,
    price_per_day: float,
    agent_username: str,
) -> dict:
    """Build the JSON payload stored in rental_event.

    This function is the single source of truth for the payload structure.
    Both the seed script and the rental service should call this to ensure
    the payload shape is always consistent.
    """
    number_of_days = (end_date - start_date).days
    return {
        "vehicle": {
            "id": vehicle.get("id"),
            "brand": vehicle.get("brand"),
            "licence_plate": vehicle.get("licence_plate"),
            "colour": vehicle.get("colour"),
            "fuel_type": vehicle.get("fuel_type"),
            "spare_wheel": vehicle.get("spare_wheel"),
            "fuel_level": vehicle.get("fuel_level"),
            "automatic": vehicle.get("automatic"),
            "price_per_day": float(vehicle.get("price_per_day", 0)),
        },
        "client": {
            "id": client.get("id"),
            "last_name": client.get("last_name"),
            "first_name": client.get("first_name"),
            "nationality": client.get("nationality"),
            "national_id": client.get("national_id"),
            "licence_number": client.get("licence_number"),
            "email": client.get("email"),
            "address_line": client.get("address_line"),
            "city": client.get("city"),
            "postal_code": client.get("postal_code"),
            "country": client.get("country"),
            "phone": client.get("phone"),
        },
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "number_of_days": number_of_days,
            "price_per_day": price_per_day,
            "total": round(number_of_days * price_per_day, 2),
        },
        "agent": agent_username,
    }


# ---------------------------------------------------------------------------
# blacklist
# ---------------------------------------------------------------------------


def blacklist_factory(
    *,
    client_id: int,
    added_by: int,
    permanent: bool = True,
) -> dict:
    start = _past_date(years_ago_min=0, years_ago_max=2)
    return {
        "client_id": client_id,
        "reason": random.choice(
            [
                "Vehicle returned with damage",
                "Non-payment",
                "Aggressive behaviour",
                "Fraudulent documents",
                "Repeated late returns",
            ]
        ),
        "date_start": start,
        "date_end": (
            None if permanent else start + timedelta(days=random.randint(30, 365))
        ),
        "added_by": added_by,
    }
