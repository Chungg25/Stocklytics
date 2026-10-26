"""Engine/session setup."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stockbot.config import settings
from stockbot.store.models import Base

_engine = None
_Session: sessionmaker | None = None


def init_db(url: str | None = None) -> None:
    """Create the engine and tables. Call once at startup (tests pass sqlite:// URLs)."""
    global _engine, _Session
    url = url or settings.database_url
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    _engine = create_engine(url, **kwargs)
    Base.metadata.create_all(_engine)
    _Session = sessionmaker(bind=_engine, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    if _Session is None:
        init_db()
    assert _Session is not None
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
