"""Minimal Telegram Bot API client (sync, httpx)."""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)

API = "https://api.telegram.org"


class TelegramError(RuntimeError):
    def __init__(self, method: str, description: str, code: int | None = None):
        super().__init__(f"{method}: {description}")
        self.code = code


class Bot:
    def __init__(self, token: str, timeout: float = 20.0):
        self.token = token
        self.timeout = timeout

    def call(self, method: str, files: dict | None = None, **params: Any) -> Any:
        data = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items() if v is not None}
        try:
            if files:
                resp = httpx.post(f"{API}/bot{self.token}/{method}", data=data, files=files, timeout=self.timeout)
            else:
                resp = httpx.post(f"{API}/bot{self.token}/{method}", data=data, timeout=self.timeout)
        except httpx.HTTPError as e:
            raise TelegramError(method, f"network error: {e}") from e
        try:
            body = resp.json()
        except ValueError as e:
            raise TelegramError(method, f"HTTP {resp.status_code}", resp.status_code) from e
        if not body.get("ok"):
            raise TelegramError(method, body.get("description", "unknown error"), body.get("error_code"))
        return body.get("result")

    # --- messaging -------------------------------------------------------
    def send_message(self, chat_id: int, text: str, buttons: list[list[dict]] | None = None,
                     parse_mode: str | None = "HTML", disable_preview: bool = True) -> Any:
        return self.call(
            "sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode,
            link_preview_options={"is_disabled": disable_preview},
            reply_markup={"inline_keyboard": buttons} if buttons else None,
        )

    def send_photo(self, chat_id: int, png: bytes, caption: str | None = None,
                   buttons: list[list[dict]] | None = None, parse_mode: str | None = "HTML") -> Any:
        return self.call(
            "sendPhoto", files={"photo": ("chart.png", png, "image/png")}, chat_id=chat_id,
            caption=caption, parse_mode=parse_mode,
            reply_markup={"inline_keyboard": buttons} if buttons else None,
        )

    def answer_callback(self, callback_id: str, text: str | None = None) -> Any:
        return self.call("answerCallbackQuery", callback_query_id=callback_id, text=text)

    # --- bot setup -------------------------------------------------------
    def get_me(self) -> dict:
        return self.call("getMe")

    def set_webhook(self, url: str, secret: str, allowed_updates: list[str]) -> Any:
        return self.call("setWebhook", url=url, secret_token=secret, allowed_updates=allowed_updates)

    def set_my_commands(self, commands: list[tuple[str, str]]) -> Any:
        return self.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in commands])

    def set_my_description(self, description: str, short_description: str | None = None) -> None:
        self.call("setMyDescription", description=description)
        if short_description:
            self.call("setMyShortDescription", short_description=short_description)

    # --- Managed Bots (Bot API 9.6) --------------------------------------
    def get_managed_bot_token(self, bot_user_id: int) -> str:
        return self.call("getManagedBotToken", user_id=bot_user_id)


def url_button(text: str, url: str) -> dict:
    return {"text": text, "url": url}


def callback_button(text: str, data: str) -> dict:
    return {"text": text, "callback_data": data}


def copy_button(text: str, value: str) -> dict:
    return {"text": text, "copy_text": {"text": value}}
