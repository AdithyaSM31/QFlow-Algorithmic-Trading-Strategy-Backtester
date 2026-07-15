"""
QFlow Strategies — Base class and built-in trading strategies.

All strategies extend BaseStrategy and implement on_market().
They receive MarketEvents one at a time and return SignalEvents.

IMPORTANT: Strategies only access data through the DataHandler,
which enforces point-in-time constraints. Strategies CANNOT
peek at future data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb
from abc import ABC, abstractmethod

from app.engine.event import MarketEvent, SignalEvent, SignalType
from app.engine.data_handler import DataHandler


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    Subclasses must implement:
      - on_market(event, data_handler) -> list[SignalEvent]
    
    The data_handler provides point-in-time access to historical bars.
    """

    def __init__(self, parameters: dict):
        self.parameters = parameters

    @abstractmethod
    def on_market(
        self, event: MarketEvent, data_handler: DataHandler
    ) -> list[SignalEvent]:
        """
        Process a market event and optionally generate signals.
        
        Args:
            event: The current market bar (single symbol, single timestamp)
            data_handler: Point-in-time data access (only past + current bars)
        
        Returns:
            List of SignalEvents (can be empty if no signal)
        """
        raise NotImplementedError


class MACrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy.
    
    Generates a LONG signal when the fast MA crosses above the slow MA,
    and an EXIT signal when the fast MA crosses below the slow MA.
    
    Parameters:
        fast_window (int): Fast moving average period (default: 10)
        slow_window (int): Slow moving average period (default: 50)
    """

    def __init__(self, parameters: dict):
        super().__init__(parameters)
        self.fast_window: int = parameters.get("fast_window", 10)
        self.slow_window: int = parameters.get("slow_window", 50)

    def on_market(
        self, event: MarketEvent, data_handler: DataHandler
    ) -> list[SignalEvent]:
        # Need at least slow_window + 1 bars for crossover detection
        bars = data_handler.get_all_bars_so_far(event.symbol)
        if len(bars) < self.slow_window + 1:
            return []

        closes = bars["close"].values

        # Compute MAs using ONLY point-in-time data
        fast_ma_now = np.mean(closes[-self.fast_window:])
        slow_ma_now = np.mean(closes[-self.slow_window:])
        fast_ma_prev = np.mean(closes[-self.fast_window - 1:-1])
        slow_ma_prev = np.mean(closes[-self.slow_window - 1:-1])

        signals = []

        # Golden cross: fast crosses above slow
        if fast_ma_prev <= slow_ma_prev and fast_ma_now > slow_ma_now:
            signals.append(
                SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    signal_type=SignalType.LONG,
                    strength=1.0,
                )
            )

        # Death cross: fast crosses below slow
        elif fast_ma_prev >= slow_ma_prev and fast_ma_now < slow_ma_now:
            signals.append(
                SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    signal_type=SignalType.EXIT,
                    strength=1.0,
                )
            )

        return signals


class RSIStrategy(BaseStrategy):
    """
    RSI Mean Reversion Strategy.
    
    Buys when RSI drops below oversold threshold (mean reversion entry),
    sells when RSI rises above overbought threshold (take profit).
    
    Parameters:
        period (int): RSI calculation period (default: 14)
        overbought (float): Overbought threshold (default: 70)
        oversold (float): Oversold threshold (default: 30)
    """

    def __init__(self, parameters: dict):
        super().__init__(parameters)
        self.period: int = parameters.get("period", 14)
        self.overbought: float = parameters.get("overbought", 70.0)
        self.oversold: float = parameters.get("oversold", 30.0)

    def _compute_rsi(self, closes: np.ndarray) -> float | None:
        """Compute RSI using only the provided (point-in-time) data."""
        if len(closes) < self.period + 1:
            return None

        deltas = np.diff(closes[-(self.period + 1):])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def on_market(
        self, event: MarketEvent, data_handler: DataHandler
    ) -> list[SignalEvent]:
        bars = data_handler.get_all_bars_so_far(event.symbol)
        if len(bars) < self.period + 2:
            return []

        closes = bars["close"].values
        rsi = self._compute_rsi(closes)

        if rsi is None:
            return []

        signals = []

        if rsi < self.oversold:
            signals.append(
                SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    signal_type=SignalType.LONG,
                    strength=min(1.0, (self.oversold - rsi) / self.oversold),
                )
            )

        elif rsi > self.overbought:
            signals.append(
                SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    signal_type=SignalType.EXIT,
                    strength=min(1.0, (rsi - self.overbought) / (100 - self.overbought)),
                )
            )

        return signals


class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands Mean Reversion Strategy.
    
    Buys when price touches the lower band (oversold),
    sells when price touches the upper band (overbought).
    
    Parameters:
        window (int): Moving average window (default: 20)
        num_std (float): Number of standard deviations (default: 2.0)
    """

    def __init__(self, parameters: dict):
        super().__init__(parameters)
        self.window: int = parameters.get("window", 20)
        self.num_std: float = parameters.get("num_std", 2.0)

    def on_market(
        self, event: MarketEvent, data_handler: DataHandler
    ) -> list[SignalEvent]:
        bars = data_handler.get_all_bars_so_far(event.symbol)
        if len(bars) < self.window + 1:
            return []

        closes = bars["close"].values
        window_data = closes[-self.window:]

        sma = np.mean(window_data)
        std = np.std(window_data, ddof=1)

        upper_band = sma + (self.num_std * std)
        lower_band = sma - (self.num_std * std)

        current_price = event.close
        signals = []

        # Price touches lower band — mean reversion buy
        if current_price <= lower_band:
            # Strength based on distance below lower band
            band_width = upper_band - lower_band
            if band_width > 0:
                strength = min(1.0, (lower_band - current_price) / band_width + 0.5)
            else:
                strength = 0.5

            signals.append(
                SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    signal_type=SignalType.LONG,
                    strength=strength,
                )
            )

        # Price touches upper band — take profit
        elif current_price >= upper_band:
            signals.append(
                SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    signal_type=SignalType.EXIT,
                    strength=1.0,
                )
            )

        return signals


class MLSignalStrategy(BaseStrategy):
    """
    Machine Learning Signal Strategy using XGBoost.
    
    Dynamically engineers features from historical bars, trains an XGBoost model
    on a rolling window, and predicts the next day's direction.
    
    Parameters:
        train_window (int): Number of bars to train on (default: 200).
        retrain_freq (int): Retrain model every N bars (default: 20).
        threshold (float): Probability threshold for LONG signal (default: 0.55).
    """

    def __init__(self, parameters: dict):
        super().__init__(parameters)
        self.train_window = parameters.get("train_window", 200)
        self.retrain_freq = parameters.get("retrain_freq", 20)
        self.threshold = parameters.get("threshold", 0.55)
        self.model = None
        self.bars_since_train = 0
        self.is_trained = False

    def _build_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        """Engineer technical features from price data."""
        # Create a copy to avoid SettingWithCopyWarning
        df = df.copy()
        
        # Features: returns
        df['ret_1d'] = df['close'].pct_change(1)
        df['ret_5d'] = df['close'].pct_change(5)
        df['ret_10d'] = df['close'].pct_change(10)
        
        # Features: volatility
        df['vol_20d'] = df['ret_1d'].rolling(20).std()
        
        # Features: moving averages distance
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['dist_sma_20'] = df['close'] / df['sma_20'] - 1
        df['dist_sma_50'] = df['close'] / df['sma_50'] - 1
        
        # Target: 1 if next day goes UP, else 0
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        # Drop NaNs (loses the first 50 rows due to SMA50, and last row due to target shift)
        # We handle the last row separately when predicting.
        df.dropna(inplace=True)
        
        features = ['ret_1d', 'ret_5d', 'ret_10d', 'vol_20d', 'dist_sma_20', 'dist_sma_50']
        X = df[features]
        y = df['target']
        
        return X, y, features

    def on_market(
        self, event: MarketEvent, data_handler: DataHandler
    ) -> list[SignalEvent]:
        # Need enough data for features (50) + training window
        bars = data_handler.get_all_bars_so_far(event.symbol)
        min_bars_needed = 50 + self.train_window
        
        if len(bars) < min_bars_needed:
            return []

        # Determine if we need to train
        if not self.is_trained or self.bars_since_train >= self.retrain_freq:
            # Get the training window (exclude the very last bar as target is unknown)
            train_df = bars.iloc[-self.train_window - 50 : -1]
            X_train, y_train, self.features = self._build_features(train_df)
            
            if len(X_train) > 0:
                self.model = xgb.XGBClassifier(
                    n_estimators=50, max_depth=3, learning_rate=0.1, 
                    objective='binary:logistic', random_state=42
                )
                self.model.fit(X_train, y_train)
                self.is_trained = True
                self.bars_since_train = 0

        self.bars_since_train += 1

        # Prediction phase
        if not self.is_trained:
            return []

        # Build features for current bar (using last 50 bars to compute current MAs)
        current_df = bars.iloc[-50:].copy()
        current_df['ret_1d'] = current_df['close'].pct_change(1)
        current_df['ret_5d'] = current_df['close'].pct_change(5)
        current_df['ret_10d'] = current_df['close'].pct_change(10)
        current_df['vol_20d'] = current_df['ret_1d'].rolling(20).std()
        current_df['sma_20'] = current_df['close'].rolling(20).mean()
        current_df['sma_50'] = current_df['close'].rolling(50).mean()
        current_df['dist_sma_20'] = current_df['close'] / current_df['sma_20'] - 1
        current_df['dist_sma_50'] = current_df['close'] / current_df['sma_50'] - 1

        # Extract features for the latest bar
        X_now = current_df.iloc[-1:][self.features]
        
        if X_now.isnull().values.any():
            return []

        prob_up = self.model.predict_proba(X_now)[0][1]

        signals = []
        if prob_up > self.threshold:
            # Strength proportional to confidence above threshold
            strength = min(1.0, (prob_up - self.threshold) / (1 - self.threshold))
            signals.append(
                SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    signal_type=SignalType.LONG,
                    strength=max(0.1, strength),
                )
            )
        elif prob_up < (1 - self.threshold):
            signals.append(
                SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    signal_type=SignalType.EXIT,
                    strength=1.0,
                )
            )

        return signals


# Strategy registry — maps type strings to classes
STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "MA_CROSSOVER": MACrossoverStrategy,
    "RSI": RSIStrategy,
    "BOLLINGER": BollingerBandsStrategy,
    "ML_SIGNAL": MLSignalStrategy,
}


def create_strategy(strategy_type: str, parameters: dict) -> BaseStrategy:
    """Factory function to instantiate a strategy by type name."""
    cls = STRATEGY_REGISTRY.get(strategy_type)
    if cls is None:
        raise ValueError(
            f"Unknown strategy type: {strategy_type}. "
            f"Available: {list(STRATEGY_REGISTRY.keys())}"
        )
    return cls(parameters)
