"""User model — staff accounts."""

from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class User(TimestampMixin, Base):
    """A member of staff who can operate the system.

    Roles
    -----
    admin   Full access including blacklist management and user administration.
    agent   Day-to-day operations: clients, vehicles, rentals.

    The surrogate integer PK means renaming a user (fixing a typo in
    ``username``) does not cascade through every foreign key.
    """

    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'agent')", name="chk_user_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="agent")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    reservations: Mapped[list["Reservation"]] = relationship(  # noqa: F821
        back_populates="created_by_user"
    )
    active_rentals: Mapped[list["ActiveRental"]] = relationship(  # noqa: F821
        back_populates="opened_by_user"
    )
    rental_events: Mapped[list["RentalEvent"]] = relationship(  # noqa: F821
        back_populates="recorded_by_user"
    )
    rental_archives: Mapped[list["RentalArchive"]] = relationship(  # noqa: F821
        back_populates="closed_by_user"
    )
    blacklist_entries: Mapped[list["Blacklist"]] = relationship(  # noqa: F821
        back_populates="added_by_user"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"
