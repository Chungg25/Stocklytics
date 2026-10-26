from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import make_ohlc
from stockbot import service
from stockbot.bot.manager import ManagerBot
from stockbot.bot.provisioner import LoginPrompt
from stockbot.store.db import session_scope
from stockbot.store.models import BotUser
from stockbot.store.security import decrypt, hash_api_key


class FakeBot:
    def __init__(self):
        self.sent: list[tuple[int, str, list | None]] = []

    def send_message(self, chat_id, text, buttons=None, **_):
        self.sent.append((chat_id, text, buttons))

    def answer_callback(self, *_a, **_k):
        pass

    def get_managed_bot_token(self, bot_user_id):
        assert bot_user_id == 999
        return "999:SECRET"


class FakeProvisioner:
    def __init__(self):
        self.calls = []

    def provision(self, uid, token, api_key):
        self.calls.append(("provision", uid, token, api_key))
        return f"c-{uid}"

    def update_token(self, uid, token, api_key):
        self.calls.append(("update_token", uid, token))

    def start_chatgpt_login(self, uid, on_prompt, on_done):
        on_prompt(LoginPrompt(url="https://auth.openai.com/codex/device", code="ABCD-1234"))
        on_done(True, "")

    def restart(self, uid):
        pass

    def stop(self, uid):
        self.calls.append(("stop", uid))


@pytest.fixture()
def manager(monkeypatch):
    bot, prov = FakeBot(), FakeProvisioner()
    m = ManagerBot(bot, prov, "StocklyticsHubBot")
    monkeypatch.setattr(m, "_setup_personal_bot", lambda token: None)
    return m, bot, prov


def test_full_onboarding_flow(fresh_db, manager):
    m, bot, prov = manager
    m.handle_update({"update_id": 1, "message": {"chat": {"type": "private"}, "from": {"id": 42, "first_name": "Ann"},
                                                   "text": "/start connect"}})
    welcome = bot.sent[-1]
    assert "Create my bot" in welcome[2][0][0]["text"]
    assert welcome[2][0][0]["url"].startswith("https://t.me/newbot/StocklyticsHubBot/stocklytics_")

    m.handle_update({"update_id": 2, "managed_bot": {"user": {"id": 42, "first_name": "Ann"},
                                                      "bot": {"id": 999, "username": "ann_trader_bot"}}})
    kind, uid, token, api_key = prov.calls[0]
    assert (kind, uid, token) == ("provision", 42, "999:SECRET")
    texts = [t for _, t, _ in bot.sent]
    assert any("ABCD-1234" in t for t in texts)          # ChatGPT code relayed
    assert "All set" in texts[-1]                         # login finished
    with session_scope() as s:
        u = s.scalar(select(BotUser).where(BotUser.telegram_user_id == 42))
        assert u.status == "active" and u.bot_username == "ann_trader_bot"
        assert decrypt(u.bot_token_enc) == "999:SECRET"   # stored encrypted
        assert u.api_key_hash == hash_api_key(api_key)
    assert service.authenticate(api_key) == u.id


def test_strategy_tools_end_to_end(fresh_db, manager, monkeypatch):
    m, _, prov = manager
    m.handle_update({"managed_bot": {"user": {"id": 7}, "bot": {"id": 999, "username": "b_bot"}}})
    api_key = prov.calls[0][3]
    uid = service.authenticate(api_key)

    dsl = {"name": "Osc", "universe": {"tickers": ["AAA"]},
           "entry": {"left": {"price": "close"}, "op": "crosses_above", "right": 14},
           "exit": {"left": {"price": "close"}, "op": "crosses_below", "right": 12}}
    assert "BUY when" in service.validate(dsl)["summary"]
    saved = service.save_strategy(uid, dsl)

    df = make_ohlc([10 + (i % 20) for i in range(400)], start="2023-01-02")
    monkeypatch.setattr("stockbot.backtest.runner.get_daily", lambda t, s, e: {x: df for x in t})
    monkeypatch.setattr(service, "parse_period", lambda *a: (date(2023, 6, 1), date(2024, 6, 1)))
    bt = service.backtest(uid, strategy_id=saved["id"], send_chart=False)
    assert bt["portfolio"]["total_trades"] > 0

    monkeypatch.setattr(service, "market_status", lambda: type("S", (), {"session": "closed"})())
    on = service.set_alerts(uid, saved["id"], True)
    assert on["status"] == "active" and "every 30 minutes" in on["message"]
    listed = service.list_strategies(uid)["strategies"][0]
    assert listed["last_backtest"]["trades"] == bt["portfolio"]["total_trades"]

    other = BotUser(telegram_user_id=8, status="active")
    with session_scope() as s:
        s.add(other)
    with pytest.raises(service.UserError):
        service.get_strategy(other.id, saved["id"])       # users cannot see each other's strategies


def test_mcp_requires_api_key(fresh_db):
    from stockbot.app import app
    with TestClient(app) as c:
        headers = {"Accept": "application/json, text/event-stream"}
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}}
        r = c.post("/mcp", json=init, headers=headers)
        sid = r.headers.get("mcp-session-id")
        h = {**headers, "mcp-session-id": sid, "mcp-protocol-version": "2025-06-18"} if sid else headers
        c.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=h)
        r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                 "params": {"name": "list_strategies", "arguments": {}}}, headers=h)
        assert "Missing API key" in r.text
