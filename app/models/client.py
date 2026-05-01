"""Client model — people who rent vehicles."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Client(TimestampMixin, Base):
    """A person who rents (or may rent) a vehicle.

    Address blocks
    --------------
    The domestic address uses France as the default country.
    The foreign address block is optional and used for non-resident renters.

    Identity documents
    ------------------
    Both a national ID and a passport may be stored; either may be null
    depending on the client's nationality and what they present.

    Soft delete
    -----------
    Clients are never hard-deleted: ``is_deleted = True`` hides them from
    the UI while preserving referential integrity on historical rentals.
    """

    __tablename__ = "client"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Identity documents
    national_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    licence_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    licence_issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    passport_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    passport_issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Domestic address (default country: France)
    address_line: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str] = mapped_column(
        String(50), nullable=False, default="France"
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Foreign address
    foreign_address_line: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    foreign_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    foreign_country: Mapped[str | None] = mapped_column(String(50), nullable=True)
    foreign_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Contact / consent
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Second driver flag; the actual second driver is on active_rental
    has_second_driver: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    reservations: Mapped[list["Reservation"]] = relationship(  # noqa: F821
        back_populates="client", foreign_keys="Reservation.client_id"
    )
    active_rentals: Mapped[list["ActiveRental"]] = relationship(  # noqa: F821
        back_populates="client", foreign_keys="ActiveRental.client_id"
    )
    active_rentals_as_second_driver: Mapped[list["ActiveRental"]] = relationship(  # noqa: F821
        back_populates="second_driver",
        foreign_keys="ActiveRental.second_driver_id",
    )
    rental_archives: Mapped[list["RentalArchive"]] = relationship(  # noqa: F821
        back_populates="client"
    )
    blacklist_entries: Mapped[list["Blacklist"]] = relationship(  # noqa: F821
        back_populates="client"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return (
            f"<Client id={self.id} name={self.full_name!r} "
            f"email={self.email!r}>"
        )
