"""
Database seeder — populates the database with realistic fake data.

Run from the project root:

    python db/seeds/seed.py

Or with a custom count:

    python db/seeds/seed.py --users 3 --clients 20 --vehicles 15 --rentals 30

What gets created
-----------------
1. Two fixed users: one admin ("alice") and one agent ("bob").
   Additional random agents are created based on --users.
2. Clients (default: 15)
3. Vehicles (default: 10, mix of statuses)
4. Past rentals with events and archives (default: 20)
5. A small number of open active rentals
6. One blacklisted client
7. Notifications for archived rentals whose client has email_consent

All existing data is cleared before seeding (idempotent).
"""

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Make sure the project root is on sys.path when running directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
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
    admin_factory,
    available_vehicle_factory,
    blacklist_factory,
    client_factory,
    rental_event_payload,
    rented_vehicle_factory,
    reservation_factory,
    user_factory,
    vehicle_factory,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear(db: Session) -> None:
    """Delete all rows in dependency order (children before parents)."""
    print("  Clearing existing data...")
    for model in [
        Notification,
        RentalArchive,
        RentalEvent,
        ActiveRental,
        Reservation,
        Blacklist,
        Vehicle,
        Client,
        User,
    ]:
        db.query(model).delete()
    db.commit()


def _past_rental_dates() -> tuple[date, date]:
    """Return (start, end) in the past, 1–30 days ago."""
    end = date.today() - timedelta(days=random.randint(1, 30))
    start = end - timedelta(days=random.randint(1, 7))
    return start, end


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


def seed_users(db: Session, n_extra: int = 1) -> list[User]:
    """Create fixed admin + agent accounts, plus n_extra random agents."""
    users = []

    alice = User(**admin_factory(username="alice"))
    bob = User(**user_factory(username="bob", role="agent"))
    db.add_all([alice, bob])
    db.flush()
    users.extend([alice, bob])

    for _ in range(n_extra):
        user = User(**user_factory())
        db.add(user)
        db.flush()
        users.append(user)

    print(f"  Created {len(users)} users")
    return users


def seed_clients(db: Session, n: int = 15) -> list[Client]:
    clients = []
    for _ in range(n):
        client = Client(**client_factory())
        db.add(client)
        db.flush()
        clients.append(client)
    print(f"  Created {len(clients)} clients")
    return clients


def seed_vehicles(db: Session, n: int = 10) -> list[Vehicle]:
    vehicles = []
    # Ensure a mix: at least 3 available, 2 rented, rest random
    for _ in range(min(3, n)):
        v = Vehicle(**available_vehicle_factory())
        db.add(v)
        db.flush()
        vehicles.append(v)

    for _ in range(min(2, max(0, n - 3))):
        v = Vehicle(**rented_vehicle_factory())
        db.add(v)
        db.flush()
        vehicles.append(v)

    for _ in range(max(0, n - 5)):
        v = Vehicle(**vehicle_factory())
        db.add(v)
        db.flush()
        vehicles.append(v)

    print(f"  Created {len(vehicles)} vehicles")
    return vehicles


def seed_past_rentals(
    db: Session,
    users: list[User],
    clients: list[Client],
    vehicles: list[Vehicle],
    n: int = 20,
) -> list[RentalArchive]:
    """Create completed rentals: event + archive for each."""
    archives = []
    agent = next((u for u in users if u.role == "agent"), users[0])

    # Use vehicles not currently rented for past rentals
    available = [v for v in vehicles if v.status != "rented"]
    if not available:
        available = vehicles

    for _ in range(n):
        vehicle = random.choice(available)
        client = random.choice(clients)
        start, end = _past_rental_dates()
        price = float(vehicle.price_per_day)

        # Optionally create a prior reservation (70% of the time)
        reservation = None
        if random.random() > 0.3:
            reservation = Reservation(
                **reservation_factory(
                    vehicle_id=vehicle.id,
                    client_id=client.id,
                    created_by=agent.id,
                    start_date=start,
                    end_date=end,
                    price_per_day=price,
                )
            )
            db.add(reservation)
            db.flush()

        # Build the immutable event payload
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
            reservation_id=reservation.id if reservation else None,
            vehicle_id=vehicle.id,
            client_id=client.id,
            closed_by=agent.id,
            start_date=start,
            end_date=end,
            price_per_day=price,
        )
        db.add(archive)
        db.flush()
        archives.append(archive)

        # Notification if client has email consent
        if client.email_consent and client.email:
            notif = Notification(
                archive_id=archive.id,
                type="invoice",
                recipient=client.email,
                status="sent",
                provider_msg_id=f"mock_{archive.id}_{random.randint(1000, 9999)}",
            )
            db.add(notif)

    db.flush()
    print(f"  Created {len(archives)} past rentals (events + archives)")
    return archives


def seed_active_rentals(
    db: Session,
    users: list[User],
    clients: list[Client],
    vehicles: list[Vehicle],
    n: int = 3,
) -> list[ActiveRental]:
    """Create a small number of currently open rentals."""
    rented = [v for v in vehicles if v.status == "rented"]
    agent = next((u for u in users if u.role == "agent"), users[0])
    active = []

    for _i, vehicle in enumerate(rented[:n]):
        client = random.choice(clients)
        start = date.today() - timedelta(days=random.randint(1, 3))
        expected_end = date.today() + timedelta(days=random.randint(1, 5))
        price = float(vehicle.price_per_day)

        rental = ActiveRental(
            **active_rental_factory(
                vehicle_id=vehicle.id,
                client_id=client.id,
                opened_by=agent.id,
                start_date=start,
                expected_end_date=expected_end,
                price_per_day=price,
            )
        )
        db.add(rental)
        active.append(rental)

    db.flush()
    print(f"  Created {len(active)} active rentals")
    return active


def seed_blacklist(
    db: Session,
    clients: list[Client],
    users: list[User],
) -> None:
    admin = next((u for u in users if u.role == "admin"), users[0])
    client = random.choice(clients)
    entry = Blacklist(**blacklist_factory(client_id=client.id, added_by=admin.id))
    db.add(entry)
    db.flush()
    print(f"  Created 1 blacklist entry (client_id={client.id})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def seed(
    n_users: int = 1,
    n_clients: int = 15,
    n_vehicles: int = 10,
    n_rentals: int = 20,
) -> None:
    print("Starting seed...")
    with SessionLocal() as db:
        _clear(db)
        users = seed_users(db, n_extra=n_users)
        clients = seed_clients(db, n=n_clients)
        vehicles = seed_vehicles(db, n=n_vehicles)
        seed_past_rentals(db, users, clients, vehicles, n=n_rentals)
        seed_active_rentals(db, users, clients, vehicles)
        seed_blacklist(db, clients, users)
        db.commit()
    print("Seed complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the car rental database.")
    parser.add_argument("--users", type=int, default=1, help="Extra agents to create")
    parser.add_argument("--clients", type=int, default=15)
    parser.add_argument("--vehicles", type=int, default=10)
    parser.add_argument("--rentals", type=int, default=20)
    args = parser.parse_args()

    seed(
        n_users=args.users,
        n_clients=args.clients,
        n_vehicles=args.vehicles,
        n_rentals=args.rentals,
    )
