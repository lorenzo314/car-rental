"""Notification model — outbound email audit trail."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.rental_archive import RentalArchive


from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Notification(TimestampMixin, Base):
    """A record of an outbound email sent by the system.

    Every email attempt is logged here regardless of outcome.  The
    ``provider_msg_id`` field stores the ID returned by the email
    provider (Resend), which can be used to query delivery status or
    raise a support ticket.

    Retry policy
    ------------
    The system does not automatically retry failed sends.  A background
    task should periodically query ``status = 'failed'`` rows and
    attempt resending — this is noted as a known limitation in the README.
    """

    __tablename__ = "notification"
    __table_args__ = (
        CheckConstraint(
            "type IN ('invoice', 'return_reminder', 'overdue_alert')",
            name="chk_notification_type",
        ),
        CheckConstraint(
            "status IN ('sent', 'failed', 'bounced', 'pending')",
            name="chk_notification_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    archive_id: Mapped[int] = mapped_column(
        ForeignKey("rental_archive.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    recipient: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    provider_msg_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationships
    rental_archive: Mapped[RentalArchive] = relationship(back_populates="notifications")

    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id} type={self.type!r} "
            f"recipient={self.recipient!r} status={self.status!r}>"
        )
