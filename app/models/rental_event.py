"""RentalEvent model — the immutable event log."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.rental_archive import RentalArchive
    from app.models.user import User


from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RentalEvent(Base):
    """An immutable record of a rental closure.

    One row is written when a rental is closed.  It is never updated
    or deleted.  The ``payload`` JSON column contains a complete snapshot
    of the vehicle and client as they were at the moment of closure.

    This table is intentionally NOT in 3NF.  The ``payload`` duplicates
    data from ``client`` and ``vehicle``.  This is correct because
    normalisation guards against update anomalies — and update anomalies
    cannot occur on a table that is never updated.  The purpose of this
    table is to record what was true at a specific past moment, independent
    of any future changes to the operational tables.

    TimestampMixin is NOT applied here: ``recorded_at`` is set once at
    insert time and must never be overwritten by an ``ON UPDATE`` trigger.

    Soft foreign keys
    -----------------
    ``vehicle_id`` and ``client_id`` are stored for convenience but are
    NOT declared as FOREIGN KEYs.  A vehicle or client may be soft-deleted
    without invalidating history.

    Payload structure (example)
    ---------------------------
    {
        "vehicle": {
            "id": 6,
            "brand": "Renault Clio",
            "licence_plate": "AB-123-CD",
            "colour": "red",
            "fuel_type": "petrol",
            "spare_wheel": true,
            "fuel_level": 100,
            "automatic": false,
            "price_per_day": 45.00
        },
        "client": {
            "id": 5,
            "last_name": "Dupont",
            "first_name": "Marie",
            "nationality": "French",
            "national_id": "123456789",
            "licence_number": "DT453432",
            "email": "marie.dupont@example.com",
            "address_line": "12 rue de la Paix",
            "city": "Paris",
            "postal_code": "75001",
            "country": "France",
            "phone": "0612345678"
        },
        "period": {
            "start_date": "2024-06-01",
            "end_date": "2024-06-05",
            "number_of_days": 4,
            "price_per_day": 45.00,
            "total": 180.00
        },
        "agent": "alice"
    }
    """

    __tablename__ = "rental_event"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('rental_closed', 'rental_cancelled', 'rental_modified')",
            name="chk_rental_event_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="rental_closed"
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    recorded_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    # Soft references — informational only, not FK-enforced
    vehicle_id: Mapped[int] = mapped_column(Integer, nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)

    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Relationships
    recorded_by_user: Mapped[User] = relationship(back_populates="rental_events")
    rental_archive: Mapped[RentalArchive | None] = relationship(back_populates="event")

    def __repr__(self) -> str:
        return (
            f"<RentalEvent id={self.id} type={self.event_type!r} "
            f"recorded_at={self.recorded_at}>"
        )
