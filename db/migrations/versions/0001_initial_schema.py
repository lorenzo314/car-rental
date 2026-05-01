"""Initial schema.

Revision ID: 0001
Revises:     (none — first migration)
Create Date: 2024-01-01 00:00:00
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# Alembic metadata
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # user
    # -----------------------------------------------------------------
    op.create_table(
        "user",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(30), nullable=False, server_default="agent"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("username", name="uq_user_username"),
        sa.CheckConstraint("role IN ('admin', 'agent')", name="chk_user_role"),
    )

    # -----------------------------------------------------------------
    # client
    # -----------------------------------------------------------------
    op.create_table(
        "client",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("nationality", sa.String(50), nullable=True),
        sa.Column("national_id", sa.String(20), nullable=True),
        sa.Column("licence_number", sa.String(30), nullable=True),
        sa.Column("licence_issued_on", sa.Date, nullable=True),
        sa.Column("passport_number", sa.String(30), nullable=True),
        sa.Column("passport_issued_on", sa.Date, nullable=True),
        sa.Column("address_line", sa.String(200), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(10), nullable=True),
        sa.Column(
            "country", sa.String(50), nullable=False, server_default="France"
        ),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("foreign_address_line", sa.String(200), nullable=True),
        sa.Column("foreign_city", sa.String(100), nullable=True),
        sa.Column("foreign_country", sa.String(50), nullable=True),
        sa.Column("foreign_phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("email_consent", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("has_second_driver", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
    )

    # -----------------------------------------------------------------
    # vehicle
    # -----------------------------------------------------------------
    op.create_table(
        "vehicle",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("brand", sa.String(100), nullable=False),
        sa.Column("licence_plate", sa.String(20), nullable=False),
        sa.Column("colour", sa.String(30), nullable=True),
        sa.Column("fuel_type", sa.String(10), nullable=False),
        sa.Column("spare_wheel", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("fuel_level", sa.Integer, nullable=True),
        sa.Column("automatic", sa.Boolean, nullable=False, server_default="0"),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="available"
        ),
        sa.Column("price_per_day", sa.Numeric(10, 2), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("licence_plate", name="uq_vehicle_plate"),
        sa.CheckConstraint(
            "status IN ('available', 'rented', 'maintenance', 'retired')",
            name="chk_vehicle_status",
        ),
        sa.CheckConstraint(
            "fuel_type IN ('petrol', 'diesel', 'electric', 'hybrid')",
            name="chk_fuel_type",
        ),
        sa.CheckConstraint("fuel_level BETWEEN 0 AND 100", name="chk_fuel_level"),
    )

    # -----------------------------------------------------------------
    # reservation
    # -----------------------------------------------------------------
    op.create_table(
        "reservation",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("price_per_day", sa.Numeric(10, 2), nullable=False),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicle.id"), nullable=False),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("client.id"), nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("end_date >= start_date", name="chk_reservation_dates"),
    )
    op.create_index(
        "idx_reservation_vehicle_dates",
        "reservation",
        ["vehicle_id", "start_date", "end_date"],
    )

    # -----------------------------------------------------------------
    # active_rental
    # -----------------------------------------------------------------
    op.create_table(
        "active_rental",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "reservation_id",
            sa.Integer,
            sa.ForeignKey("reservation.id"),
            nullable=True,
        ),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicle.id"), nullable=False),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("client.id"), nullable=False),
        sa.Column(
            "second_driver_id",
            sa.Integer,
            sa.ForeignKey("client.id"),
            nullable=True,
        ),
        sa.Column("opened_by", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("expected_end_date", sa.Date, nullable=False),
        sa.Column("price_per_day", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "expected_end_date >= start_date", name="chk_active_rental_dates"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'overdue')", name="chk_active_rental_status"
        ),
    )
    op.create_index(
        "idx_active_rental_vehicle_dates",
        "active_rental",
        ["vehicle_id", "start_date", "expected_end_date"],
    )

    # -----------------------------------------------------------------
    # rental_event  (no TimestampMixin — recorded_at must never update)
    # -----------------------------------------------------------------
    op.create_table(
        "rental_event",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "event_type", sa.String(30), nullable=False, server_default="rental_closed"
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("recorded_by", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("vehicle_id", sa.Integer, nullable=False),   # soft ref
        sa.Column("client_id", sa.Integer, nullable=False),    # soft ref
        sa.Column("payload", sa.JSON, nullable=False),
        sa.CheckConstraint(
            "event_type IN ('rental_closed', 'rental_cancelled', 'rental_modified')",
            name="chk_rental_event_type",
        ),
    )

    # -----------------------------------------------------------------
    # rental_archive
    # -----------------------------------------------------------------
    op.create_table(
        "rental_archive",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "event_id", sa.Integer, sa.ForeignKey("rental_event.id"), nullable=False
        ),
        sa.Column(
            "reservation_id",
            sa.Integer,
            sa.ForeignKey("reservation.id"),
            nullable=True,
        ),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicle.id"), nullable=False),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("client.id"), nullable=False),
        sa.Column("closed_by", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("price_per_day", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("end_date >= start_date", name="chk_archive_dates"),
    )
    op.create_index("idx_archive_client", "rental_archive", ["client_id"])
    op.create_index("idx_archive_vehicle", "rental_archive", ["vehicle_id"])
    op.create_index(
        "idx_archive_dates", "rental_archive", ["start_date", "end_date"]
    )

    # -----------------------------------------------------------------
    # blacklist
    # -----------------------------------------------------------------
    op.create_table(
        "blacklist",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("client.id"), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("date_start", sa.Date, nullable=False),
        sa.Column("date_end", sa.Date, nullable=True),
        sa.Column("added_by", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "date_end IS NULL OR date_end >= date_start", name="chk_blacklist_dates"
        ),
    )
    op.create_index(
        "idx_blacklist_client",
        "blacklist",
        ["client_id", "date_start", "date_end"],
    )

    # -----------------------------------------------------------------
    # notification
    # -----------------------------------------------------------------
    op.create_table(
        "notification",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "archive_id",
            sa.Integer,
            sa.ForeignKey("rental_archive.id"),
            nullable=False,
        ),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("recipient", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("provider_msg_id", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "type IN ('invoice', 'return_reminder', 'overdue_alert')",
            name="chk_notification_type",
        ),
        sa.CheckConstraint(
            "status IN ('sent', 'failed', 'bounced', 'pending')",
            name="chk_notification_status",
        ),
    )
    op.create_index("idx_notification_archive", "notification", ["archive_id"])
    op.create_index("idx_vehicle_status", "vehicle", ["status"])


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("notification")
    op.drop_table("blacklist")
    op.drop_table("rental_archive")
    op.drop_table("rental_event")
    op.drop_table("active_rental")
    op.drop_table("reservation")
    op.drop_table("vehicle")
    op.drop_table("client")
    op.drop_table("user")
