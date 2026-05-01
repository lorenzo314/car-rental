"""RentalArchive model — completed rentals."""

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class RentalArchive(TimestampMixin, Base):
    """The operational record of a completed rental.

    Normalised: reads current client and vehicle data via JOIN.
    Links to ``RentalEvent`` for the immutable historical snapshot used
    when generating invoices or resolving disputes.

    Computed properties
    -------------------
    ``number_of_days`` and ``total`` are Python properties rather than
    database-generated columns.  This keeps the model portable across
    MySQL and SQLite (used in tests) without dialect-specific DDL.
    The values are consistent by construction — they cannot be set
    independently of ``start_date``, ``end_date``, and ``price_per_day``.
    """

    __tablename__ = "rental_archive"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="chk_archive_dates"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("rental_event.id"), nullable=False)
    reservation_id: Mapped[int | None] = mapped_column(
        ForeignKey("reservation.id"), nullable=True
    )
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id"), nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), nullable=False)
    closed_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_per_day: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Rate applied, EUR",
    )

    # Relationships
    event: Mapped["RentalEvent"] = relationship(  # noqa: F821
        back_populates="rental_archive"
    )
    reservation: Mapped["Reservation | None"] = relationship(  # noqa: F821
        back_populates="rental_archive"
    )
    vehicle: Mapped["Vehicle"] = relationship(  # noqa: F821
        back_populates="rental_archives"
    )
    client: Mapped["Client"] = relationship(  # noqa: F821
        back_populates="rental_archives"
    )
    closed_by_user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="rental_archives"
    )
    notifications: Mapped[list["Notification"]] = relationship(  # noqa: F821
        back_populates="rental_archive"
    )

    @property
    def number_of_days(self) -> int:
        return (self.end_date - self.start_date).days

    @property
    def total(self) -> float:
        return self.number_of_days * float(self.price_per_day)

    def __repr__(self) -> str:
        return (
            f"<RentalArchive id={self.id} vehicle_id={self.vehicle_id} "
            f"client_id={self.client_id} "
            f"{self.start_date} → {self.end_date} "
            f"total={self.total:.2f} EUR>"
        )
