"""
技术指标计算 - BMAD Model Layer
"""
import pandas as pd
import numpy as np
from typing import Optional


class TechnicalIndicators:
    """技术指标计算工具类"""
    
    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """简单移动平均"""
        return series.rolling(window=period).mean()
    
    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """指数移动平均"""
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """相对强弱指标"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """MACD指标"""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> tuple:
        """布林带"""
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """平均真实波幅"""
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                   k_period: int = 14, d_period: int = 3) -> tuple:
        """随机指标"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()
        
        return k, d
    
    @staticmethod
    def momentum(series: pd.Series, period: int = 10) -> pd.Series:
        """动量指标"""
        return series.diff(period)
    
    @staticmethod
    def roc(series: pd.Series, period: int = 10) -> pd.Series:
        """变化率"""
        return (series - series.shift(period)) / series.shift(period) * 100
    
    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """威廉指标"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        
        wr = -100 * (highest_high - close) / (highest_high - lowest_low)
        return wr
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """平均趋向指标"""
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = TechnicalIndicators.atr(high, low, close, 1) * 1  # TR without smoothing
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """成交量加权平均价"""
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """能量潮"""
        direction = np.where(close > close.shift(1), 1, np.where(close < close.shift(1), -1, 0))
        obv = (volume * direction).cumsum()
        return pd.Series(obv, index=close.index)
