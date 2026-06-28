"""Repository layer: data-access abstractions per aggregate."""

from app.repositories.base import BaseRepository
from app.repositories.job import JobRepository

__all__ = ["BaseRepository", "JobRepository"]
