"""
历史评分计算模块。

对单只股票遍历历史每一天，用"当天及之前"的数据计算得分，
严格避免未来数据泄露。
"""

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from stock_cli.cache import load_cache
from stock_cli.screener import analyze_stock, MIN_DATA_ROWS


@dataclass
class DayScore:
    """单只股票某一天的得分快照。"""
    date: str           # YYYY-MM-DD
    symbol: str
    score: int
    signals: List[str]  # 触发的信号名称列表


def compute_score_history(symbol: str, min_rows: int = MIN_DATA_ROWS) -> List[DayScore]:
    """
    读取缓存，对每个交易日用截止当天的历史数据计算得分。

    参数:
        symbol: 股票代码，如 600519.SS
        min_rows: 计算得分所需的最少历史行数（默认与 screener 一致）

    返回:
        按日期升序排列的 DayScore 列表。数据不足或缺失时返回空列表。
    """
    df = load_cache(symbol)
    if df.empty or len(df) < min_rows:
        return []

    df = df.sort_index()
    results: List[DayScore] = []

    for i in range(min_rows, len(df) + 1):
        window = df.iloc[:i]
        result = analyze_stock(symbol, window)
        if result.error:
            continue

        date_str = str(window.index[-1].date())
        triggered = [s.name for s in result.signals if s.triggered]
        results.append(DayScore(
            date=date_str,
            symbol=symbol,
            score=result.total_score,
            signals=triggered,
        ))

    return results
