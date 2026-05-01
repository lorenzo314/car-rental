"""ActiveRental model — a vehicle that is currently out."""

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ActiveRental(TimestampMixin, Base):
    """A vehicle that is currently rented out.

    Lifecycle
    ---------
    Created when a vehicle leaves the lot (with or without a prior
    reservation).  Deleted — and a ``RentalArchive`` + ``RentalEvent``
    row written — when the vehicle is returned.

    Walk-ins
    --------
    ``reservation_id`` is nullable.  A walk-in client goes directly to
    an ``ActiveRental`` without a prior ``Reservation``.

    Second driver
    -------------
    ``second_driver_id`` resolves the identity of the second driver as
    a proper foreign key to ``client``, rather than a mere boolean flag.
    """

    __tablename__ = "active_rental"
    __table_args__ = (
        CheckConstraint(
            "expected_end_date >= start_date", name="chk_active_rental_dates"
        ),
        CheckConstraint(
            "status IN ('active', 'overdue')", name="chk_active_rental_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reservation_id: Mapped[int | None] = mapped_column(
        ForeignKey("reservation.id"), nullable=True
    )
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id"), nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), nullable=False)
    second_driver_id: Mapped[int | None] = mapped_column(
        ForeignKey("client.id"), nullable=True
    )
    opened_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_per_day: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Agreed rate for this rental, EUR",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )

    # Relationships
    reservation: Mapped["Reservation | None"] = relationship(  # noqa: F821
        back_populates="active_rental"
    )
    vehicle: Mapped["Vehicle"] = relationship(  # noqa: F821
        back_populates="active_rentals"
    )
    client: Mapped["Client"] = relationship(  # noqa: F821
        back_populates="active_rentals", foreign_keys=[client_id]
    )
    second_driver: Mapped["Client | None"] = relationship(  # noqa: F821
        back_populates="active_rentals_as_second_driver",
        foreign_keys=[second_driver_id],
    )
    opened_by_user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="active_rentals"
    )

    @property
    def number_of_days(self) -> int:
        return (self.expected_end_date - self.start_date).days

    @property
    def expected_total(self) -> float:
        return self.number_of_days * float(self.price_per_day)

    def __repr__(self) -> str:
        return (
            f"<ActiveRental id={self.id} vehicle_id={self.vehicle_id} "
            f"client_id={self.client_id} status={self.status!r}>"
        )
