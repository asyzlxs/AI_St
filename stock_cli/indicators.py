import pandas as pd
import numpy as np


def moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """计算 MA5, MA20, MA60 均线。"""
    close = df["Close"]
    return pd.DataFrame({
        "MA5": close.rolling(window=5).mean(),
        "MA20": close.rolling(window=20).mean(),
        "MA60": close.rolling(window=60).mean(),
    }, index=df.index)


def detect_golden_cross(ma5: pd.Series, ma20: pd.Series) -> bool:
    """检测近3个交易日内 MA5 是否上穿 MA20（金叉）。"""
    if len(ma5) < 4 or len(ma20) < 4:
        return False
    ma5_clean = ma5.dropna()
    ma20_clean = ma20.dropna()
    if len(ma5_clean) < 4 or len(ma20_clean) < 4:
        return False
    # 对齐索引
    common = ma5_clean.index.intersection(ma20_clean.index)
    if len(common) < 4:
        return False
    m5 = ma5_clean.loc[common]
    m20 = ma20_clean.loc[common]
    # 当前 MA5 > MA20，且 3 天前 MA5 <= MA20
    return bool(m5.iloc[-1] > m20.iloc[-1] and m5.iloc[-4] <= m20.iloc[-4])


def detect_bullish_alignment(close: pd.Series, ma5: pd.Series,
                              ma20: pd.Series, ma60: pd.Series) -> bool:
    """检测多头排列: Close > MA5 > MA20 > MA60。"""
    vals = []
    for s in [close, ma5, ma20, ma60]:
        last = s.dropna()
        if len(last) == 0:
            return False
        vals.append(float(last.iloc[-1]))
    return vals[0] > vals[1] > vals[2] > vals[3]


def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算 RSI (Wilder's smoothing)。"""
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(100.0)  # 全涨无跌时 RSI=100
    return rsi


def detect_rsi_oversold_bounce(rsi: pd.Series, lookback: int = 10) -> bool:
    """检测 RSI 超卖反弹: 近 lookback 日内 RSI 曾低于 30，当前回升到 30 以上。"""
    rsi_clean = rsi.dropna()
    if len(rsi_clean) < lookback:
        return False
    recent = rsi_clean.iloc[-lookback:]
    current = float(rsi_clean.iloc[-1])
    was_oversold = bool((recent < 30).any())
    return was_oversold and current > 30


def compute_macd(df: pd.DataFrame,
                  fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """计算 MACD 线、信号线和柱状图。"""
    close = df["Close"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({
        "MACD": macd_line,
        "Signal": signal_line,
        "Histogram": histogram,
    }, index=df.index)


def detect_macd_histogram_turn_positive(histogram: pd.Series) -> bool:
    """检测 MACD 柱状图从负转正。"""
    h = histogram.dropna()
    if len(h) < 2:
        return False
    return bool(h.iloc[-1] > 0 and h.iloc[-2] <= 0)


def detect_macd_bottom_divergence(close: pd.Series, macd_line: pd.Series,
                                   lookback: int = 60) -> bool:
    """检测 MACD 底背离（简化版）：价格创新低但 MACD 未创新低。

    将 lookback 窗口分为前后两半，比较各自的最低点。
    """
    c = close.dropna()
    m = macd_line.dropna()
    common = c.index.intersection(m.index)
    if len(common) < lookback:
        return False
    c = c.loc[common].iloc[-lookback:]
    m = m.loc[common].iloc[-lookback:]
    half = lookback // 2
    close_low_first = float(c.iloc[:half].min())
    close_low_second = float(c.iloc[half:].min())
    macd_low_first = float(m.iloc[:half].min())
    macd_low_second = float(m.iloc[half:].min())
    # 价格创新低，但 MACD 没创新低 → 底背离
    return close_low_second < close_low_first and macd_low_second > macd_low_first


def detect_volume_surge(df: pd.DataFrame, threshold: float = 2.0,
                         avg_period: int = 20) -> bool:
    """检测放量: 当日成交量 > threshold 倍的 avg_period 日均量。"""
    vol = df["Volume"].dropna()
    if len(vol) < avg_period + 1:
        return False
    avg_vol = float(vol.iloc[-(avg_period + 1):-1].mean())
    if avg_vol <= 0:
        return False
    current_vol = float(vol.iloc[-1])
    return current_vol > threshold * avg_vol


def detect_price_breakout(df: pd.DataFrame, period: int = 60) -> bool:
    """检测价格突破: 当日收盘价为近 period 日新高。"""
    close = df["Close"].dropna()
    if len(close) < period:
        return False
    current = float(close.iloc[-1])
    prev_high = float(close.iloc[-period:-1].max())
    return current >= prev_high


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算 ATR (Average True Range)。"""
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift(1)).abs()
    low_close = (df["Low"] - df["Close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=period).mean()


def detect_atr_squeeze_breakout(atr: pd.Series,
                                 squeeze_period: int = 20,
                                 expansion_threshold: float = 1.5) -> bool:
    """检测波动率突破: ATR 收缩后放大。

    近 squeeze_period 日内 ATR 最低值 < 均值 * 0.75（收缩发生），
    且当前 ATR > 最低值 * expansion_threshold（放大确认）。
    """
    atr_clean = atr.dropna()
    if len(atr_clean) < squeeze_period + 1:
        return False
    window = atr_clean.iloc[-(squeeze_period + 1):-1]
    avg_atr = float(window.mean())
    min_atr = float(window.min())
    current_atr = float(atr_clean.iloc[-1])
    if avg_atr <= 0 or min_atr <= 0:
        return False
    squeeze = min_atr < avg_atr * 0.75
    expansion = current_atr > min_atr * expansion_threshold
    return squeeze and expansion
