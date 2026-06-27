"""Reusable Pydantic schemas shared across the API surface."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    """Base class for response schemas that map from ORM models."""

    model_config = ConfigDict(from_attributes=True)


class HealthStatus(BaseModel):
    """Payload returned by the health-check endpoint."""

    status: str = Field(description="`ok` when the service is healthy.")
    service: str = Field(description="Human-readable service name.")
    version: str = Field(description="Application version.")
    environment: str = Field(description="Active environment (development, production, ...).")


class ErrorResponse(BaseModel):
    """Standard error envelope produced by the global exception handler."""

    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Human-readable error message.")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Optional structured details."
    )
