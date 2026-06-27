"""Configuration package exposing the application settings singleton."""

from app.config.settings import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
