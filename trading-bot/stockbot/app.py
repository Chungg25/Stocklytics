"""FastAPI app: QR landing page, manager-bot webhook, MCP endpoint, health. Run: uvicorn stockbot.app:app"""
from __future__ import annotations

import hmac
import io
import logging
from contextlib import asynccontextmanager
from html import escape

import segno
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

from stockbot import scheduler
from stockbot.bot.manager import ManagerBot
from stockbot.bot.provisioner import DockerProvisioner
from stockbot.bot.telegram import Bot
from stockbot.config import settings
from stockbot.mcp_server import mcp
from stockbot.store.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("stockbot")

WEBHOOK_PATH = "/telegram/manager"
mcp_app = mcp.streamable_http_app(streamable_http_path="/mcp", host="0.0.0.0")
_manager: ManagerBot | None = None


def manager() -> ManagerBot:
    global _manager
    if _manager is None:
        if not settings.manager_bot_token or not settings.manager_bot_username:
            raise HTTPException(503, "Manager bot is not configured")
        _manager = ManagerBot(Bot(settings.manager_bot_token), DockerProvisioner(), settings.manager_bot_username)
    return _manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.manager_bot_token and settings.telegram_webhook_secret:
        try:
            Bot(settings.manager_bot_token).set_webhook(
                f"{settings.public_base_url}{WEBHOOK_PATH}", settings.telegram_webhook_secret,
                ["message", "callback_query", "managed_bot"])
            log.info("manager webhook registered")
        except Exception:
            log.exception("could not register manager webhook")
    if settings.enable_scheduler:
        scheduler.start()
    async with mcp_app.router.lifespan_context(mcp_app):
        yield
    scheduler.stop()


app = FastAPI(title="Stocklytics Trading Bot", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request, background: BackgroundTasks,
                           x_telegram_bot_api_secret_token: str | None = Header(default=None)) -> dict:
    if not settings.telegram_webhook_secret or not hmac.compare_digest(
            x_telegram_bot_api_secret_token or "", settings.telegram_webhook_secret):
        raise HTTPException(403)
    update = await request.json()
    background.add_task(manager().handle_update, update)
    return {"ok": True}


@app.get("/connect", response_class=HTMLResponse)
def connect_page() -> str:
    link = manager().start_link()
    buf = io.BytesIO()
    segno.make(link, error="m").save(buf, kind="svg", scale=8, border=2, dark="#111827", light="#ffffff")
    svg = buf.getvalue().decode()
    return CONNECT_HTML.replace("{{QR}}", svg).replace("{{LINK}}", escape(link))


CONNECT_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stock Alerts on Telegram</title>
<style>
:root{--bg:#f8fafc;--card:#fff;--text:#0f172a;--muted:#475569;--accent:#229ED9;--line:#e2e8f0}
@media (prefers-color-scheme:dark){:root{--bg:#0b1220;--card:#111a2e;--text:#e2e8f0;--muted:#94a3b8;--line:#1e293b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:460px;margin:0 auto;padding:32px 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:28px 22px;text-align:center}
h1{font-size:1.5rem;margin:0 0 6px}p.sub{color:var(--muted);margin:0 0 22px}
.qr{display:inline-block;background:#fff;border-radius:16px;padding:10px}.qr svg{width:220px;height:220px;display:block}
.btn{display:block;margin:20px 0 6px;padding:14px;border-radius:14px;background:var(--accent);color:#fff;text-decoration:none;font-weight:600}
ol{text-align:left;padding-left:22px;margin:22px 0 0}li{margin:8px 0}small{color:var(--muted);display:block;margin-top:18px}
</style></head><body><main><div class="card">
<h1>📈 Your stock-alert bot</h1>
<p class="sub">Describe a strategy in plain English. Get a backtest. Get alerts on Telegram.</p>
<div class="qr">{{QR}}</div>
<a class="btn" href="{{LINK}}">Open in Telegram</a>
<ol>
<li><b>Scan</b> the code with your phone camera (or tap the button) and press <b>Start</b>.</li>
<li>Tap <b>Create my bot</b>, then <b>Create</b>.</li>
<li><b>Sign in with ChatGPT</b> and paste the code you're given.</li>
<li>Open your new bot and say hi 👋</li>
</ol>
<small>Notifications only — it never places trades. Not financial advice.</small>
</div></main></body></html>"""

# MCP endpoint (POST/GET /mcp). Mounted last so the routes above take precedence.
app.mount("/", mcp_app)
