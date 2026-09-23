# -*- coding: utf-8 -*-

"""Middleware package initialization.

This project currently uses a lightweight polling setup, so the middleware layer
is kept as a compatibility no-op until concrete middleware handlers are added.
"""

from typing import Any


def setup_middleware(bot: Any, db: Any) -> None:
    """Register bot middleware when available.

    The current codebase does not yet implement middleware-specific logic, but
    the app bootstrap expects this function to exist and return without error.
    """
    return None


__all__ = ["setup_middleware"]
