"""
Integration tests — ORM models against a real (SQLite in-memory) database.

These tests exercise actual database writes, reads, relationships, and
constraints.  They use the shared fixtures from conftest.py and rely on
the per-test transaction rollback to stay isolated.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    ActiveRental,
    Blacklist,
    Client,
    Notification,
    RentalArchive,
    Reservation,
    User,
    Vehicle,
)
from db.seeds.factories import (
    active_rental_factory,
    blacklist_factory,
    vehicle_factory,
)


class TestUserPersistence:
    def test_create_and_read(self, db: Session, agent: User) -> None:
        found = db.query(User).filter_by(username="test_agent").first()
        assert found is not None
        assert found.role == "agent"
        assert found.is_active is True

    def test_username_is_unique(self, db: Session, agent: User) -> None:
        duplicate = User(
            username="test_agent",
            password_hash="hash",
            role="agent",
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.flush()

    def test_default_role_is_agent(self, db: Session) -> None:
        user = User(username="newagent", password_hash="hash")
        db.add(user)
        db.flush()
        assert user.role == "agent"


class TestClientPersistence:
    def test_create_and_read(self, db: Session, client: Client) -> None:
        found = db.query(Client).filter_by(id=client.id).first()
        assert found is not None
        assert found.country == "France"
        assert found.is_deleted is False

    def test_soft_delete(self, db: Session, client: Client) -> None:
        client.is_deleted = True
        client.deleted_at = date.today()
        db.flush()

        found = db.query(Client).filter_by(id=client.id).first()
        assert found.is_deleted is True
        assert found.deleted_at is not None

    def test_full_name_property(self, db: Session, client: Client) -> None:
        assert client.full_name == f"{client.first_name} {client.last_name}"


class TestVehiclePersistence:
    def test_create_and_read(self, db: Session, vehicle: Vehicle) -> None:
        found = db.query(Vehicle).filter_by(id=vehicle.id).first()
        assert found is not None
        assert found.status == "available"
        assert found.is_available is True

    def test_licence_plate_is_unique(self, db: Session, vehicle: Vehicle) -> None:
        data = vehicle_factory(status="available")
        data["licence_plate"] = vehicle.licence_plate  # duplicate
        duplicate = Vehicle(**data)
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.flush()

    def test_status_transition(self, db: Session, vehicle: Vehicle) -> None:
        vehicle.status = "rented"
        db.flush()
        assert vehicle.is_available is False


class TestReservationPersistence:
    def test_create_with_relationships(
        self, db: Session, vehicle: Vehicle, client: Client, agent: User
    ) -> None:
        reservation = Reservation(
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=4),
            price_per_day=50.00,
            vehicle_id=vehicle.id,
            client_id=client.id,
            created_by=agent.id,
        )
        db.add(reservation)
        db.flush()

        assert reservation.id is not None
        assert reservation.number_of_days == 3
        assert reservation.total == 150.00

    def test_relationship_loading(
        self, db: Session, vehicle: Vehicle, client: Client, agent: User
    ) -> None:
        reservation = Reservation(
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=3),
            price_per_day=45.00,
            vehicle_id=vehicle.id,
            client_id=client.id,
            created_by=agent.id,
        )
        db.add(reservation)
        db.flush()
        db.refresh(reservation)

        assert reservation.vehicle.brand == vehicle.brand
        assert reservation.client.full_name == client.full_name
        assert reservation.created_by_user.username == agent.username


class TestActiveRentalPersistence:
    def test_create_walk_in(
        self, db: Session, vehicle: Vehicle, client: Client, agent: User
    ) -> None:
        """Walk-in: no reservation_id."""
        rental = ActiveRental(
            **active_rental_factory(
                vehicle_id=vehicle.id,
                client_id=client.id,
                opened_by=agent.id,
            )
        )
        db.add(rental)
        db.flush()

        assert rental.id is not None
        assert rental.reservation_id is None
        assert rental.status == "active"

    def test_second_driver_relationship(
        self,
        db: Session,
        vehicle: Vehicle,
        client: Client,
        second_driver: Client,
        agent: User,
    ) -> None:
        rental = ActiveRental(
            **active_rental_factory(
                vehicle_id=vehicle.id,
                client_id=client.id,
                opened_by=agent.id,
                second_driver_id=second_driver.id,
            )
        )
        db.add(rental)
        db.flush()
        db.refresh(rental)

        assert rental.second_driver is not None
        assert rental.second_driver.id == second_driver.id


class TestRentalArchivePersistence:
    def test_computed_properties(
        self, db: Session, rental_archive: RentalArchive
    ) -> None:
        assert rental_archive.number_of_days == 4
        assert rental_archive.total == 180.00  # 4 days × 45.00

    def test_event_relationship(
        self, db: Session, rental_archive: RentalArchive
    ) -> None:
        db.refresh(rental_archive)
        assert rental_archive.event is not None
        assert rental_archive.event.event_type == "rental_closed"

    def test_payload_structure(
        self, db: Session, rental_archive: RentalArchive
    ) -> None:
        db.refresh(rental_archive)
        payload = rental_archive.event.payload
        assert "vehicle" in payload
        assert "client" in payload
        assert "period" in payload
        assert "agent" in payload
        assert payload["period"]["number_of_days"] == 4
        assert payload["period"]["total"] == 180.00

    def test_walk_in_has_no_reservation(
        self, db: Session, rental_archive: RentalArchive
    ) -> None:
        assert rental_archive.reservation_id is None


class TestBlacklistPersistence:
    def test_permanent_ban(self, db: Session, client: Client, admin: User) -> None:
        entry = Blacklist(
            **blacklist_factory(client_id=client.id, added_by=admin.id, permanent=True)
        )
        db.add(entry)
        db.flush()

        assert entry.date_end is None

    def test_temporary_ban(self, db: Session, client: Client, admin: User) -> None:
        entry = Blacklist(
            **blacklist_factory(client_id=client.id, added_by=admin.id, permanent=False)
        )
        db.add(entry)
        db.flush()

        assert entry.date_end is not None
        assert entry.date_end >= entry.date_start

    def test_client_relationship(
        self, db: Session, client: Client, admin: User
    ) -> None:
        entry = Blacklist(**blacklist_factory(client_id=client.id, added_by=admin.id))
        db.add(entry)
        db.flush()
        db.refresh(entry)

        assert entry.client.id == client.id


class TestNotificationPersistence:
    def test_create_notification(
        self, db: Session, rental_archive: RentalArchive, client: Client
    ) -> None:
        notif = Notification(
            archive_id=rental_archive.id,
            type="invoice",
            recipient=client.email,
            status="sent",
            provider_msg_id="mock_abc123",
        )
        db.add(notif)
        db.flush()

        assert notif.id is not None
        assert notif.status == "sent"

    def test_relationship_to_archive(
        self, db: Session, rental_archive: RentalArchive, client: Client
    ) -> None:
        notif = Notification(
            archive_id=rental_archive.id,
            type="invoice",
            recipient=client.email,
            status="pending",
        )
        db.add(notif)
        db.flush()
        db.refresh(notif)

        assert notif.rental_archive.id == rental_archive.id
