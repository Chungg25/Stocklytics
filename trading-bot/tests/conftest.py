import os
import tempfile

from cryptography.fernet import Fernet

# Must be set before stockbot.config is imported.
os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db"))
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("ENABLE_SCHEDULER", "false")
os.environ.setdefault("MAX_QUOTE_AGE_SECONDS", "300")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from stockbot.store import db  # noqa: E402


@pytest.fixture()
def fresh_db(tmp_path):
    db.init_db(f"sqlite:///{tmp_path / 'db.sqlite'}")
    yield


def make_ohlc(closes, start="2024-01-02", opens=None, highs=None, lows=None, volume=1_000_000.0) -> pd.DataFrame:
    closes = np.asarray(closes, dtype=float)
    idx = pd.bdate_range(start, periods=len(closes))
    opens = closes if opens is None else np.asarray(opens, dtype=float)
    highs = np.maximum(opens, closes) if highs is None else np.asarray(highs, dtype=float)
    lows = np.minimum(opens, closes) if lows is None else np.asarray(lows, dtype=float)
    return pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volume}, index=idx)
