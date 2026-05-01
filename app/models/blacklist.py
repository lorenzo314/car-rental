"""Blacklist model — clients refused service."""

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Blacklist(TimestampMixin, Base):
    """A record of a client who has been refused service.

    A client may appear more than once (separate incidents).  The PK is
    therefore ``id``, not ``client_id``.

    ``date_end``
    ------------
    NULL means the ban is permanent.  Setting a date allows the ban to
    be lifted on a specific day — the application should check
    ``date_end IS NULL OR date_end >= today`` when deciding whether a
    client is currently blacklisted.
    """

    __tablename__ = "blacklist"
    __table_args__ = (
        CheckConstraint(
            "date_end IS NULL OR date_end >= date_start",
            name="chk_blacklist_dates",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_start: Mapped[date] = mapped_column(Date, nullable=False)
    date_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    added_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    # Relationships
    client: Mapped["Client"] = relationship(  # noqa: F821
        back_populates="blacklist_entries"
    )
    added_by_user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="blacklist_entries"
    )

    def __repr__(self) -> str:
        return (
            f"<Blacklist id={self.id} client_id={self.client_id} "
            f"date_start={self.date_start} date_end={self.date_end}>"
        )
