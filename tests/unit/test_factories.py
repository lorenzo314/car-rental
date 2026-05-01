"""
Unit tests for the Faker-based factory functions.

Verifies that each factory produces dicts with the correct structure,
types, and constraints — without touching the database.
"""

from datetime import date

from db.seeds.factories import (
    admin_factory,
    blacklist_factory,
    client_factory,
    rental_event_payload,
    reservation_factory,
    user_factory,
    vehicle_factory,
)


class TestUserFactory:
    def test_returns_required_keys(self) -> None:
        data = user_factory()
        assert {"username", "password_hash", "role", "is_active"} <= data.keys()

    def test_default_role_is_agent(self) -> None:
        assert user_factory()["role"] == "agent"

    def test_admin_factory_sets_admin_role(self) -> None:
        assert admin_factory()["role"] == "admin"

    def test_username_override(self) -> None:
        assert user_factory(username="alice")["username"] == "alice"

    def test_password_hash_is_not_plaintext(self) -> None:
        data = user_factory()
        assert data["password_hash"] != "password123"
        assert data["password_hash"].startswith("$2b$")


class TestClientFactory:
    def test_returns_required_keys(self) -> None:
        data = client_factory()
        required = {
            "last_name", "first_name", "country", "email",
            "email_consent", "is_deleted",
        }
        assert required <= data.keys()

    def test_default_country_is_france(self) -> None:
        assert client_factory()["country"] == "France"

    def test_not_deleted_by_default(self) -> None:
        data = client_factory()
        assert data["is_deleted"] is False
        assert data["deleted_at"] is None

    def test_deleted_flag(self) -> None:
        data = client_factory(is_deleted=True)
        assert data["is_deleted"] is True
        assert data["deleted_at"] is not None

    def test_produces_different_values(self) -> None:
        """Two calls should produce different clients (Faker is not static)."""
        a = client_factory()
        b = client_factory()
        # At minimum the email should differ
        assert a["email"] != b["email"]


class TestVehicleFactory:
    def test_returns_required_keys(self) -> None:
        data = vehicle_factory()
        required = {"brand", "licence_plate", "fuel_type", "price_per_day", "status"}
        assert required <= data.keys()

    def test_fuel_level_in_range(self) -> None:
        for _ in range(20):
            level = vehicle_factory()["fuel_level"]
            assert 0 <= level <= 100

    def test_price_per_day_positive(self) -> None:
        for _ in range(10):
            assert vehicle_factory()["price_per_day"] > 0

    def test_status_override(self) -> None:
        assert vehicle_factory(status="maintenance")["status"] == "maintenance"


class TestReservationFactory:
    def test_end_date_after_start(self) -> None:
        data = reservation_factory(vehicle_id=1, client_id=1, created_by=1)
        assert data["end_date"] >= data["start_date"]

    def test_explicit_dates(self) -> None:
        start = date(2025, 1, 10)
        end = date(2025, 1, 15)
        data = reservation_factory(
            vehicle_id=1, client_id=1, created_by=1,
            start_date=start, end_date=end,
        )
        assert data["start_date"] == start
        assert data["end_date"] == end


class TestRentalEventPayload:
    def _make_payload(self) -> dict:
        vehicle = vehicle_factory()
        vehicle["id"] = 1
        vehicle["price_per_day"] = 50.0
        client = client_factory()
        client["id"] = 2
        return rental_event_payload(
            vehicle=vehicle,
            client=client,
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 5),
            price_per_day=50.0,
            agent_username="alice",
        )

    def test_top_level_keys(self) -> None:
        payload = self._make_payload()
        assert set(payload.keys()) == {"vehicle", "client", "period", "agent"}

    def test_period_calculations(self) -> None:
        payload = self._make_payload()
        period = payload["period"]
        assert period["number_of_days"] == 4
        assert period["total"] == 200.0
        assert period["price_per_day"] == 50.0

    def test_dates_are_iso_strings(self) -> None:
        payload = self._make_payload()
        assert payload["period"]["start_date"] == "2024-06-01"
        assert payload["period"]["end_date"] == "2024-06-05"

    def test_agent_username(self) -> None:
        assert self._make_payload()["agent"] == "alice"


class TestBlacklistFactory:
    def test_permanent_ban_has_no_end_date(self) -> None:
        data = blacklist_factory(client_id=1, added_by=1, permanent=True)
        assert data["date_end"] is None

    def test_temporary_ban_has_end_date(self) -> None:
        data = blacklist_factory(client_id=1, added_by=1, permanent=False)
        assert data["date_end"] is not None
        assert data["date_end"] >= data["date_start"]

    def test_reason_is_non_empty_string(self) -> None:
        data = blacklist_factory(client_id=1, added_by=1)
        assert isinstance(data["reason"], str)
        assert len(data["reason"]) > 0
