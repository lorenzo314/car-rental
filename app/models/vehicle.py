"""Vehicle model — the rental fleet."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Vehicle(TimestampMixin, Base):
    """A vehicle available (or previously available) for rental.

    Status
    ------
    available   Ready to rent.
    rented      Currently out with a client.
    maintenance Under repair or scheduled service.
    retired     Removed from the fleet; kept for historical records.

    The status column makes availability an O(1) read rather than a
    subquery over active_rental.  It is updated transactionally whenever
    a rental is opened or closed.

    Soft delete
    -----------
    Vehicles are never hard-deleted. ``status = 'retired'`` combined with
    ``is_deleted = True`` hides them from the UI.
    """

    __tablename__ = "vehicle"
    __table_args__ = (
        CheckConstraint(
            "status IN ('available', 'rented', 'maintenance', 'retired')",
            name="chk_vehicle_status",
        ),
        CheckConstraint(
            "fuel_type IN ('petrol', 'diesel', 'electric', 'hybrid')",
            name="chk_fuel_type",
        ),
        CheckConstraint(
            "fuel_level BETWEEN 0 AND 100",
            name="chk_fuel_level",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    licence_plate: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    colour: Mapped[str | None] = mapped_column(String(30), nullable=True)
    fuel_type: Mapped[str] = mapped_column(String(10), nullable=False)
    spare_wheel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fuel_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Fuel level percentage 0–100",
    )
    automatic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available"
    )
    price_per_day: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Daily rental rate in EUR",
    )
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    reservations: Mapped[list["Reservation"]] = relationship(  # noqa: F821
        back_populates="vehicle"
    )
    active_rentals: Mapped[list["ActiveRental"]] = relationship(  # noqa: F821
        back_populates="vehicle"
    )
    rental_archives: Mapped[list["RentalArchive"]] = relationship(  # noqa: F821
        back_populates="vehicle"
    )

    @property
    def is_available(self) -> bool:
        return self.status == "available" and not self.is_deleted

    def __repr__(self) -> str:
        return (
            f"<Vehicle id={self.id} brand={self.brand!r} "
            f"plate={self.licence_plate!r} status={self.status!r}>"
        )
