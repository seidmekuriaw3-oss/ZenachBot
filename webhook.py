# -*- coding: utf-8 -*-

"""Minimal webhook server for the ZenachBot Telegram bot.

This module is intentionally lightweight so the project can run in webhook mode
without depending on a more complete application bootstrap.
"""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, request
from telebot import TeleBot
from telebot.types import Update

from config import Config
from database import Database
from handlers import register_handlers
from middleware import setup_middleware

logger = logging.getLogger(__name__)

config = Config()
app = Flask(__name__)

db = None
bot = None


def init_runtime() -> None:
    """Create the database and bot only when the webhook runtime is actually used."""
    global db, bot
    if db is None:
        db = Database()
    if bot is None:
        bot = TeleBot(config.bot.TOKEN, parse_mode='HTML')
        setup_middleware(bot, db)
        register_handlers(bot, db)



@app.route('/', methods=['GET'])
def index() -> str:
    return 'ZenachBot webhook service is running.'


@app.route('/webhook', methods=['POST'])
def webhook_handler() -> str:
    """Accept Telegram webhook updates and push them to the bot."""
    init_runtime()
    secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    expected_secret = config.bot.WEBHOOK_SECRET
    if not expected_secret or secret != expected_secret:
        return 'Unauthorized', 401
    if not request.is_json:
        return 'Bad Request', 400

    try:
        update = Update.de_json(request.get_data(as_text=True))
        if update:
            bot.process_new_updates([update])
        return 'OK', 200
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception('Webhook update processing failed: %s', exc)
        return 'Internal Server Error', 500


if __name__ == '__main__':
    init_runtime()
    app.run(host='0.0.0.0', port=config.bot.WEBHOOK_PORT)
