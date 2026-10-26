"""The onboarding ("manager") bot users reach by scanning the QR code.

Flow for a non-technical user:
  1. Scan QR → Telegram opens this bot → tap Start
  2. Tap "Create my bot" → Telegram's own create-bot screen (pre-filled) → tap Create
  3. Tap "Sign in with ChatGPT", log in, paste the code (copy button provided)
  4. Tap "Open my bot" and start chatting
Everything else (token, server, AI wiring) happens automatically.
"""
from __future__ import annotations

import logging
import secrets
from html import escape
from urllib.parse import quote

from sqlalchemy import select

from stockbot.bot.provisioner import LoginPrompt, Provisioner
from stockbot.bot.telegram import Bot, TelegramError, callback_button, copy_button, url_button
from stockbot.store.db import session_scope
from stockbot.store.models import BotUser
from stockbot.store.security import encrypt, hash_api_key, new_api_key

log = logging.getLogger(__name__)

BOT_NAME = "My Trading Alerts"
TRY_IT = ("Try: <i>“Alert me when AAPL or MSFT RSI crosses above 30 while the price is above the 200-day "
          "average; sell when RSI goes above 70, stop-loss 7%.”</i>")


class ManagerBot:
    def __init__(self, bot: Bot, provisioner: Provisioner, username: str):
        self.bot = bot
        self.provisioner = provisioner
        self.username = username

    # ------------------------------------------------------------------ links
    def newbot_link(self) -> str:
        suggested = f"stocklytics_{secrets.token_hex(3)}_bot"
        return f"https://t.me/newbot/{self.username}/{suggested}?name={quote(BOT_NAME)}"

    def start_link(self) -> str:
        return f"https://t.me/{self.username}?start=connect"

    # ------------------------------------------------------------------ dispatcher
    def handle_update(self, update: dict) -> None:
        try:
            if "managed_bot" in update:
                self._on_managed_bot(update["managed_bot"])
            elif "callback_query" in update:
                self._on_callback(update["callback_query"])
            elif "message" in update:
                self._on_message(update["message"])
        except Exception:
            log.exception("manager bot failed on update %s", update.get("update_id"))

    def _on_message(self, msg: dict) -> None:
        if msg.get("chat", {}).get("type") != "private":
            return
        user = msg.get("from") or {}
        uid = user.get("id")
        text = (msg.get("text") or "").strip()
        if msg.get("managed_bot_created"):
            return  # handled through the managed_bot update
        if text.startswith("/status"):
            return self._send_status(uid)
        if text.startswith("/relogin"):
            return self._relogin(uid)
        if text.startswith("/remove"):
            return self.bot.send_message(uid, "Remove your trading bot? Your strategies and alerts will stop.",
                                         [[callback_button("Yes, remove it", "remove"),
                                           callback_button("Cancel", "noop")]])
        self._welcome(uid, user.get("first_name") or "there")

    def _on_callback(self, cq: dict) -> None:
        uid = cq["from"]["id"]
        data = cq.get("data")
        try:
            self.bot.answer_callback(cq["id"])
        except TelegramError:
            pass
        if data == "relogin":
            self._relogin(uid)
        elif data == "remove":
            self._remove(uid)

    # ------------------------------------------------------------------ steps
    def _welcome(self, uid: int, first_name: str) -> None:
        with session_scope() as s:
            existing = s.scalar(select(BotUser).where(BotUser.telegram_user_id == uid))
        if existing and existing.status == "active" and existing.bot_username:
            self.bot.send_message(
                uid,
                f"You're all set, {escape(first_name)} ✅\nYour bot: @{existing.bot_username}\n\n{TRY_IT}",
                [[url_button(f"💬 Open @{existing.bot_username}", f"https://t.me/{existing.bot_username}")],
                 [callback_button("🔐 Reconnect ChatGPT", "relogin")]],
            )
            return
        if existing and existing.status == "awaiting_login":
            self.bot.send_message(uid, "Your bot is created — one step left: sign in with ChatGPT.",
                                  [[callback_button("🔐 Sign in with ChatGPT", "relogin")]])
            return
        self.bot.send_message(
            uid,
            f"Hi {escape(first_name)}! 👋\n\n"
            "I'll set up your <b>personal stock-alert bot</b>. You describe a trading idea in plain English, "
            "it backtests it on real data and, if you like it, watches the market every 30 minutes and "
            "messages you when your conditions are met.\n\n"
            "<b>Setup takes about a minute:</b>\n"
            "1️⃣ Create your bot (one tap)\n"
            "2️⃣ Sign in with ChatGPT\n"
            "3️⃣ Start chatting\n\n"
            "ℹ️ Notifications only — it never places trades.",
            [[url_button("🤖 Create my bot", self.newbot_link())]],
        )

    def _on_managed_bot(self, upd: dict) -> None:
        owner, new_bot = upd["user"], upd["bot"]
        uid = owner["id"]
        token = self.bot.get_managed_bot_token(new_bot["id"])
        api_key = new_api_key()
        with session_scope() as s:
            user = s.scalar(select(BotUser).where(BotUser.telegram_user_id == uid))
            is_token_change = bool(user and user.bot_id == new_bot["id"] and user.status == "active")
            if user is None:
                user = BotUser(telegram_user_id=uid, first_name=owner.get("first_name"))
                s.add(user)
            user.bot_id, user.bot_username = new_bot["id"], new_bot.get("username")
            user.bot_token_enc, user.api_key_hash = encrypt(token), hash_api_key(api_key)
            if not is_token_change:
                user.status = "provisioning"

        if is_token_change:
            self.provisioner.update_token(uid, token, api_key)
            return

        self.bot.send_message(uid, f"🎉 @{new_bot.get('username')} created! Setting it up — this takes ~20 seconds…")
        self._setup_personal_bot(token)
        try:
            name = self.provisioner.provision(uid, token, api_key)
        except Exception:
            log.exception("provisioning failed for %s", uid)
            self.bot.send_message(uid, "😕 Something went wrong while setting up your bot. Please tap /start to try again.")
            return
        with session_scope() as s:
            user = s.scalar(select(BotUser).where(BotUser.telegram_user_id == uid))
            user.container_name, user.status = name, "awaiting_login"
        self._relogin(uid)

    def _setup_personal_bot(self, token: str) -> None:
        """Friendly description on the user's own bot (Hermes manages its command menu)."""
        try:
            Bot(token).set_my_description(
                "Your personal stock strategy assistant: describe an idea, get a backtest, receive alerts. "
                "Notifications only — never places trades.",
                short_description="Stock strategy backtests & alerts (notifications only)",
            )
        except TelegramError as e:
            log.warning("could not configure personal bot: %s", e)

    def _relogin(self, uid: int) -> None:
        with session_scope() as s:
            user = s.scalar(select(BotUser).where(BotUser.telegram_user_id == uid))
            if user is None or not user.container_name:
                return self._welcome(uid, "there")
            username = user.bot_username

        def on_prompt(p: LoginPrompt) -> None:
            self.bot.send_message(
                uid,
                "<b>Step 2 of 3 — Sign in with ChatGPT</b>\n\n"
                "1. Tap <b>Open ChatGPT sign-in</b> and log in to your ChatGPT account\n"
                f"2. When asked, paste this code: <code>{escape(p.code)}</code>\n\n"
                "I'll message you as soon as it's done. The code expires in about 15 minutes.",
                [[url_button("🔐 Open ChatGPT sign-in", p.url)], [copy_button("📋 Copy code", p.code)]],
            )

        def on_done(ok: bool, detail: str) -> None:
            if ok:
                with session_scope() as s:
                    user = s.scalar(select(BotUser).where(BotUser.telegram_user_id == uid))
                    user.status = "active"
                self.bot.send_message(
                    uid,
                    f"✅ <b>All set!</b>\n\n<b>Step 3 of 3:</b> open @{username}, tap <b>Start</b> and describe "
                    f"your strategy.\n\n{TRY_IT}",
                    [[url_button(f"💬 Open @{username}", f"https://t.me/{username}?start=hello")]],
                )
            else:
                log.warning("ChatGPT login failed for %s: %s", uid, detail)
                self.bot.send_message(uid, "The ChatGPT sign-in didn't complete (it may have timed out). "
                                           "Tap below to get a new code.",
                                      [[callback_button("🔁 Try again", "relogin")]])

        self.provisioner.start_chatgpt_login(uid, on_prompt, on_done)

    def _send_status(self, uid: int) -> None:
        with session_scope() as s:
            user = s.scalar(select(BotUser).where(BotUser.telegram_user_id == uid))
        if user is None:
            return self._welcome(uid, "there")
        labels = {"provisioning": "setting up", "awaiting_login": "waiting for ChatGPT sign-in",
                  "active": "running ✅", "stopped": "removed"}
        self.bot.send_message(uid, f"Bot: @{user.bot_username or '—'}\nStatus: {labels.get(user.status, user.status)}")

    def _remove(self, uid: int) -> None:
        self.provisioner.stop(uid)
        with session_scope() as s:
            user = s.scalar(select(BotUser).where(BotUser.telegram_user_id == uid))
            if user:
                user.status, user.api_key_hash = "stopped", None
        self.bot.send_message(uid, "Removed. Your alerts are off. You can also delete the bot itself in "
                                   "@BotFather. Tap /start any time to set it up again.")
