# -*- coding: utf-8 -*-

"""Simple scheduler stub used by the app bootstrap."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Scheduler:
    """Compatibility wrapper for the bot scheduler.

    The project currently does not have a full asynchronous scheduler
    implementation, but main.py expects this class to exist and provide
    start()/stop() methods during startup.
    """

    def __init__(self, bot: Any = None, db: Any = None, *args, **kwargs):
        self.bot = bot
        self.db = db
        self._running = False

    def start(self) -> None:
        """Start scheduler tasks."""
        self._running = True
        logger.info("Scheduler started (stub mode)")

    def stop(self) -> None:
        """Stop scheduler tasks."""
        self._running = False
        logger.info("Scheduler stopped (stub mode)")

    def is_running(self) -> bool:
        return self._running


__all__ = ["Scheduler"]
