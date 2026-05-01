"""
Unit tests for ORM model properties and computed values.

These tests exercise pure Python logic on model instances — no database
required.  They verify that computed properties are correct and that
model constructors accept valid data.
"""

from datetime import date

from app.models import Client, RentalArchive, Vehicle
from db.seeds.factories import client_factory, vehicle_factory


class TestClientModel:
    def test_full_name(self) -> None:
        client = Client(first_name="Marie", last_name="DUPONT")
        assert client.full_name == "Marie DUPONT"

    def test_default_country(self) -> None:
        client = Client(**client_factory())
        assert client.country == "France"

    def test_factory_produces_valid_data(self) -> None:
        data = client_factory()
        assert data["last_name"]
        assert data["first_name"]
        assert data["email"]
        assert data["country"] == "France"

    def test_is_not_deleted_by_default(self) -> None:
        client = Client(**client_factory())
        assert client.is_deleted is False
        assert client.deleted_at is None


class TestVehicleModel:
    def test_is_available_when_status_available(self) -> None:
        vehicle = Vehicle(**vehicle_factory(status="available"))
        assert vehicle.is_available is True

    def test_not_available_when_rented(self) -> None:
        vehicle = Vehicle(**vehicle_factory(status="rented"))
        assert vehicle.is_available is False

    def test_not_available_when_deleted(self) -> None:
        vehicle = Vehicle(**vehicle_factory(status="available"))
        vehicle.is_deleted = True
        assert vehicle.is_available is False

    def test_not_available_when_maintenance(self) -> None:
        vehicle = Vehicle(**vehicle_factory(status="maintenance"))
        assert vehicle.is_available is False

    def test_repr_contains_key_info(self) -> None:
        vehicle = Vehicle(
            brand="Renault Clio",
            licence_plate="AB-123-CD",
            status="available",
            fuel_type="petrol",
            price_per_day=45.00,
        )
        r = repr(vehicle)
        assert "Renault Clio" in r
        assert "AB-123-CD" in r
        assert "available" in r


class TestRentalArchiveModel:
    def test_number_of_days(self) -> None:
        archive = RentalArchive(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 5),
            price_per_day=45.00,
        )
        assert archive.number_of_days == 4

    def test_total(self) -> None:
        archive = RentalArchive(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 5),
            price_per_day=45.00,
        )
        assert archive.total == 180.00

    def test_total_single_day(self) -> None:
        archive = RentalArchive(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 2),
            price_per_day=60.00,
        )
        assert archive.total == 60.00

    def test_repr_contains_total(self) -> None:
        archive = RentalArchive(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 3),
            price_per_day=50.00,
        )
        assert "100.00 EUR" in repr(archive)
