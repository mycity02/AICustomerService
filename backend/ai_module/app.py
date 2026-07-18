"""Compatibility export for the standalone Flask AI application."""

from .flask_app import app, create_ai_app

__all__ = ["app", "create_ai_app"]
