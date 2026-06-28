"""ORM models.

Importing models here ensures they are registered on `Base.metadata` so
Alembic's autogenerate detects them.
"""

from app.models.job import Job, JobEmbedding
from app.models.user import User, UserRole

__all__ = ["Job", "JobEmbedding", "User", "UserRole"]
