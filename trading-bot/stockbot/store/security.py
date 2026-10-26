"""Secrets helpers: bot-token encryption at rest and per-user API keys."""
from __future__ import annotations

import hashlib
import secrets

from cryptography.fernet import Fernet

from stockbot.config import settings

API_KEY_PREFIX = "sbk_"


def _fernet() -> Fernet:
    if not settings.token_encryption_key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not set (generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')")
    return Fernet(settings.token_encryption_key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def new_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()
