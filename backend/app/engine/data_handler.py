"""
QFlow DataHandler — Point-in-Time Market Data Feed.

This is the CRITICAL component for look-ahead bias prevention.
The DataHandler maintains an internal pointer into time-sorted data
and only exposes bars up to the current simulated time.

KEY DESIGN DECISION:
  - Strategies call get_latest_bars(N) to get the last N bars
  - They can NEVER access bars beyond current_idx
  - This structurally prevents look-ahead bias — the most common
    mistake in student backtesting projects

Interview talking point:
  "I enforced point-in-time data access at the DataHandler level.
   Strategies can only see data that existed at each simulated moment.
   Even if a strategy tries to access future data, the DataHandler
   physically cannot provide it."
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Generator

from app.engine.event import MarketEvent


class DataHandler:
    """
    Manages market data with strict point-in-time access control.
    
    The internal pointer `_current_idx` advances one bar at a time.
    Strategies only see data[:_current_idx + 1], ensuring no future
    information leaks into trading decisions.
    """

    def __init__(self, data: dict[str, pd.DataFrame]):
        """
        Args:
            data: Dict mapping symbol → DataFrame with columns:
                  [timestamp, open, high, low, close, volume]
                  Must be sorted by timestamp ascending.
        """
        self._data: dict[str, pd.DataFrame] = {}
        self._current_idx: int = -1
        self._total_bars: int = 0
        self._symbols: list[str] = list(data.keys())

        # Validate and store data sorted by time
        for symbol, df in data.items():
            df = df.sort_values("timestamp").reset_index(drop=True)
            self._data[symbol] = df

        # Use the first symbol's length as reference
        # (all symbols should have aligned timestamps)
        if self._symbols:
            self._total_bars = len(self._data[self._symbols[0]])

    @property
    def symbols(self) -> list[str]:
        return self._symbols

    @property
    def total_bars(self) -> int:
        return self._total_bars

    @property
    def current_idx(self) -> int:
        return self._current_idx

    @property
    def progress(self) -> float:
        """Returns simulation progress as a fraction [0.0, 1.0]."""
        if self._total_bars <= 0:
            return 1.0
        return min(1.0, (self._current_idx + 1) / self._total_bars)

    def get_next_bar(self) -> list[MarketEvent] | None:
        """
        Advance the pointer by exactly one bar and return MarketEvents
        for all symbols at that timestamp.
        
        Returns None when all data has been consumed.
        
        This is the ONLY way data enters the simulation —
        no other method advances the pointer.
        """
        self._current_idx += 1

        if self._current_idx >= self._total_bars:
            return None

        events = []
        for symbol in self._symbols:
            df = self._data[symbol]
            if self._current_idx < len(df):
                row = df.iloc[self._current_idx]
                event = MarketEvent(
                    timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(),
                    symbol=symbol,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                )
                events.append(event)

        return events if events else None

    def get_latest_bars(self, symbol: str, n: int = 1) -> pd.DataFrame:
        """
        Return the last N bars for a symbol, up to and including
        the current pointer position.
        
        LOOK-AHEAD BIAS PREVENTION:
          This method CANNOT return data beyond _current_idx.
          Even if the full DataFrame has 1000 rows, this will
          only return rows[:_current_idx + 1].
        """
        if symbol not in self._data:
            return pd.DataFrame()

        df = self._data[symbol]
        end = min(self._current_idx + 1, len(df))
        start = max(0, end - n)

        return df.iloc[start:end].copy()

    def get_all_bars_so_far(self, symbol: str) -> pd.DataFrame:
        """
        Return ALL bars from the start up to current pointer.
        Useful for computing rolling indicators.
        
        Still respects point-in-time: only returns data[:_current_idx+1].
        """
        if symbol not in self._data:
            return pd.DataFrame()

        df = self._data[symbol]
        end = min(self._current_idx + 1, len(df))
        return df.iloc[:end].copy()

    def get_current_price(self, symbol: str) -> float | None:
        """Get the closing price of the current bar for a symbol."""
        if symbol not in self._data or self._current_idx < 0:
            return None

        df = self._data[symbol]
        if self._current_idx < len(df):
            return float(df.iloc[self._current_idx]["close"])
        return None

    def get_current_timestamp(self) -> datetime | None:
        """Get the timestamp of the current bar."""
        if self._current_idx < 0 or not self._symbols:
            return None
        df = self._data[self._symbols[0]]
        if self._current_idx < len(df):
            return pd.Timestamp(df.iloc[self._current_idx]["timestamp"]).to_pydatetime()
        return None
