"""Combine completed daily history with a live quote into a frame whose last row is today."""
from __future__ import annotations

import numpy as np
import pandas as pd

from stockbot.data.market import to_et
from stockbot.data.quotes import Quote


def with_live_bar(history: pd.DataFrame, quote: Quote) -> pd.DataFrame:
    """Append (or replace) today's bar using the quote's open/high/low/last price.

    Volume is not provided by the quote endpoint, so it is left as NaN for the live bar:
    volume-based conditions simply evaluate to False until the official close.
    """
    day = pd.Timestamp(to_et(quote.traded_at).date())
    bar = pd.DataFrame(
        {
            "Open": [quote.open], "High": [max(quote.high, quote.price)],
            "Low": [min(quote.low, quote.price)], "Close": [quote.price], "Volume": [np.nan],
        },
        index=pd.DatetimeIndex([day]),
    )
    base = history[history.index < day]
    return pd.concat([base, bar])
