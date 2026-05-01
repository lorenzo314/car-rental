"""
ORM models package.

Importing this package is sufficient for Alembic's autogenerate to
discover all tables.  The env.py in db/migrations imports Base from
here and calls target_metadata = Base.metadata.

Import order matters: tables with no foreign keys first, then tables
that reference them.  SQLAlchemy handles circular imports at runtime,
but keeping this order makes the dependency graph explicit.
"""

from app.models.active_rental import ActiveRental
from app.models.blacklist import Blacklist
from app.models.client import Client
from app.models.notification import Notification
from app.models.rental_archive import RentalArchive
from app.models.rental_event import RentalEvent
from app.models.reservation import Reservation
from app.models.user import User
from app.models.vehicle import Vehicle

__all__ = [
    "User",
    "Client",
    "Vehicle",
    "Reservation",
    "ActiveRental",
    "RentalEvent",
    "RentalArchive",
    "Blacklist",
    "Notification",
]
