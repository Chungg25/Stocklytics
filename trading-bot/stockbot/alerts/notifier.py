"""Deliver alerts straight to the user's personal bot (no LLM involved)."""
from __future__ import annotations

import logging

from stockbot.alerts.engine import Alert
from stockbot.alerts.formatter import chart_button
from stockbot.bot.telegram import Bot
from stockbot.store.models import BotUser
from stockbot.store.security import decrypt

log = logging.getLogger(__name__)

CAPTION_LIMIT = 1024


def user_bot(user: BotUser) -> Bot:
    if not user.bot_token_enc:
        raise RuntimeError(f"user {user.id} has no bot token")
    return Bot(decrypt(user.bot_token_enc))


def send_alert(user: BotUser, alert: Alert) -> bool:
    bot = user_bot(user)
    chat_id = user.telegram_user_id  # private chat id == user id
    buttons = chart_button(alert.ticker)
    if alert.chart and len(alert.text) <= CAPTION_LIMIT:
        bot.send_photo(chat_id, alert.chart, caption=alert.text, buttons=buttons)
    else:
        bot.send_message(chat_id, alert.text, buttons=buttons)
        if alert.chart:
            bot.send_photo(chat_id, alert.chart)
    return True
