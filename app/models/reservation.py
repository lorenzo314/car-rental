"""Reservation model — optional pre-booking (intent only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.active_rental import ActiveRental
    from app.models.client import Client
    from app.models.rental_archive import RentalArchive
    from app.models.user import User
    from app.models.vehicle import Vehicle


from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Reservation(TimestampMixin, Base):
    """A future booking made before the vehicle leaves.

    A reservation represents intent, not a confirmed rental.  It is
    optional: walk-in clients go straight to ``active_rental`` with
    ``reservation_id = NULL``.

    ``price_per_day`` is locked at booking time and may differ from the
    vehicle's current rate at the time the rental actually opens.
    """

    __tablename__ = "reservation"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="chk_reservation_dates"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_per_day: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Rate locked at booking time, EUR",
    )

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id"), nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    # Relationships
    vehicle: Mapped[Vehicle] = relationship(back_populates="reservations")
    client: Mapped[Client] = relationship(
        back_populates="reservations", foreign_keys=[client_id]
    )
    created_by_user: Mapped[User] = relationship(back_populates="reservations")
    active_rental: Mapped[ActiveRental | None] = relationship(
        back_populates="reservation"
    )
    rental_archive: Mapped[RentalArchive | None] = relationship(
        back_populates="reservation"
    )

    @property
    def number_of_days(self) -> int:
        return (self.end_date - self.start_date).days

    @property
    def total(self) -> float:
        return self.number_of_days * float(self.price_per_day)

    def __repr__(self) -> str:
        return (
            f"<Reservation id={self.id} vehicle_id={self.vehicle_id} "
            f"client_id={self.client_id} "
            f"{self.start_date} → {self.end_date}>"
        )
