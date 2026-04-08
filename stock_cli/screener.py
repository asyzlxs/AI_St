import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable

import pandas as pd

from stock_cli.fetcher import fetch_stock_data
from stock_cli.indicators import (
    moving_averages, detect_golden_cross, detect_bullish_alignment,
    compute_rsi, detect_rsi_oversold_bounce,
    compute_macd, detect_macd_histogram_turn_positive, detect_macd_bottom_divergence,
    detect_volume_surge, detect_price_breakout,
    compute_atr, detect_atr_squeeze_breakout,
)


@dataclass
class SignalResult:
    """单个信号的检测结果。"""
    name: str
    label: str
    triggered: bool
    score: int
    max_score: int
    detail: str


@dataclass
class ScreenResult:
    """单只股票的完整筛选结果。"""
    symbol: str
    total_score: int
    max_possible: int
    signals: List[SignalResult]
    df: Optional[pd.DataFrame] = None
    indicators: Dict[str, pd.Series] = field(default_factory=dict)
    error: Optional[str] = None


SIGNAL_CONFIG = [
    {"name": "golden_cross",      "label": "金叉 (MA5×MA20)", "max_score": 15},
    {"name": "bullish_alignment", "label": "多头排列",         "max_score": 10},
    {"name": "rsi_bounce",        "label": "RSI超卖反弹",      "max_score": 15},
    {"name": "macd_turn",         "label": "MACD柱转正",       "max_score": 10},
    {"name": "macd_divergence",   "label": "MACD底背离",       "max_score": 20},
    {"name": "volume_surge",      "label": "放量突破",         "max_score": 10},
    {"name": "price_breakout",    "label": "60日新高",         "max_score": 10},
    {"name": "atr_squeeze",       "label": "波动率突破",       "max_score": 10},
]

MAX_POSSIBLE = sum(s["max_score"] for s in SIGNAL_CONFIG)

MIN_DATA_ROWS = 60


def analyze_stock(symbol: str, df: pd.DataFrame) -> ScreenResult:
    """对单只股票执行全部技术指标分析并评分。"""
    if len(df) < MIN_DATA_ROWS:
        return ScreenResult(
            symbol=symbol, total_score=0, max_possible=MAX_POSSIBLE,
            signals=[], df=df, error=f"数据不足 ({len(df)} 行, 需要 >= {MIN_DATA_ROWS})"
        )

    # 计算指标
    ma_df = moving_averages(df)
    rsi = compute_rsi(df)
    macd_df = compute_macd(df)
    atr = compute_atr(df)

    indicators = {
        "MA5": ma_df["MA5"],
        "MA20": ma_df["MA20"],
        "MA60": ma_df["MA60"],
        "RSI": rsi,
        "MACD": macd_df["MACD"],
        "Signal": macd_df["Signal"],
        "Histogram": macd_df["Histogram"],
        "ATR": atr,
    }

    close = df["Close"]
    last_close = float(close.iloc[-1])
    last_ma5 = float(ma_df["MA5"].dropna().iloc[-1]) if len(ma_df["MA5"].dropna()) > 0 else 0
    last_ma20 = float(ma_df["MA20"].dropna().iloc[-1]) if len(ma_df["MA20"].dropna()) > 0 else 0
    last_rsi = float(rsi.dropna().iloc[-1]) if len(rsi.dropna()) > 0 else 50

    # 逐个信号检测
    detections = {
        "golden_cross": (
            detect_golden_cross(ma_df["MA5"], ma_df["MA20"]),
            f"MA5={last_ma5:.2f}, MA20={last_ma20:.2f}"
        ),
        "bullish_alignment": (
            detect_bullish_alignment(close, ma_df["MA5"], ma_df["MA20"], ma_df["MA60"]),
            f"Close={last_close:.2f} > MA5 > MA20 > MA60"
        ),
        "rsi_bounce": (
            detect_rsi_oversold_bounce(rsi),
            f"RSI={last_rsi:.1f}"
        ),
        "macd_turn": (
            detect_macd_histogram_turn_positive(macd_df["Histogram"]),
            f"Hist={float(macd_df['Histogram'].dropna().iloc[-1]):.4f}"
        ),
        "macd_divergence": (
            detect_macd_bottom_divergence(close, macd_df["MACD"]),
            "价格新低但MACD未新低"
        ),
        "volume_surge": (
            detect_volume_surge(df),
            f"Vol={int(df['Volume'].iloc[-1]):,}"
        ),
        "price_breakout": (
            detect_price_breakout(df),
            f"Close={last_close:.2f}"
        ),
        "atr_squeeze": (
            detect_atr_squeeze_breakout(atr),
            f"ATR={float(atr.dropna().iloc[-1]):.4f}"
        ),
    }

    signals = []
    total_score = 0
    for cfg in SIGNAL_CONFIG:
        name = cfg["name"]
        triggered, detail = detections[name]
        score = cfg["max_score"] if triggered else 0
        total_score += score
        signals.append(SignalResult(
            name=name, label=cfg["label"], triggered=triggered,
            score=score, max_score=cfg["max_score"], detail=detail,
        ))

    return ScreenResult(
        symbol=symbol, total_score=total_score, max_possible=MAX_POSSIBLE,
        signals=signals, df=df, indicators=indicators,
    )


def screen_stocks(symbols: List[str], start: str, end: str,
                   on_progress: Optional[Callable] = None) -> List[ScreenResult]:
    """批量筛选股票，按得分降序返回结果。"""
    results: List[ScreenResult] = []
    total = len(symbols)

    for idx, symbol in enumerate(symbols, 1):
        if on_progress:
            on_progress(idx, total, symbol)
        try:
            df = fetch_stock_data(symbol, start, end)
            result = analyze_stock(symbol, df)
        except Exception as e:
            result = ScreenResult(
                symbol=symbol, total_score=0, max_possible=MAX_POSSIBLE,
                signals=[], error=str(e),
            )
        results.append(result)
        if idx < total:
            time.sleep(0.3)

    results.sort(key=lambda r: r.total_score, reverse=True)
    return results


def load_symbols_from_file(filepath: str) -> List[str]:
    """从文件读取股票代码列表，每行一个，忽略空行和 # 开头的注释。"""
    symbols = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                symbols.append(line)
    return symbols
