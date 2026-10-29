"""Compatibility facade redirecting to app.engine.page_policy."""
from .engine.page_policy import (
    required_initial_pages,
    initial_page_records,
)

__all__ = ["required_initial_pages", "initial_page_records"]
