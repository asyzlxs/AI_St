"""
历史评分计算模块（最终优化版）。

行业动量：主进程预算好每只股票的行业动量 Series，
直接传入，score_history 内部逐日查表，O(1) 查询。
benchmark：全量传入，analyze_stock 内部按 index 对齐。
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
    date: str
    symbol: str
    score: int
    signals: List[str]


def compute_score_history(
    symbol: str,
    min_rows: int = MIN_DATA_ROWS,
    benchmark: Optional[pd.Series] = None,
    industry_mom_series: Optional[pd.Series] = None,
) -> List[DayScore]:
    """
    读取缓存，对每个交易日用截止当天的历史数据计算得分。

    benchmark          : 沪深300历史收盘价，全量传入，内部按 index 对齐
    industry_mom_series: 主进程预算的行业动量时间序列，逐日查表取值
    """
    df = load_cache(symbol)
    if df.empty or len(df) < min_rows:
        return []

    df = df.sort_index()
    results: List[DayScore] = []

    for i in range(min_rows, len(df) + 1):
        window = df.iloc[:i]
        cutoff_date = window.index[-1]

        # 行业动量：查预算序列，取 <= cutoff_date 的最新有效值
        day_industry_mom: Optional[float] = None
        if industry_mom_series is not None and not industry_mom_series.empty:
            valid = industry_mom_series.loc[:cutoff_date].dropna()
            if not valid.empty:
                day_industry_mom = float(valid.iloc[-1])

        result = analyze_stock(
            symbol, window,
            benchmark=benchmark,
            sector_dfs=None,
            precomputed_industry_mom=day_industry_mom,
        )
        if result.error:
            continue

        date_str = str(cutoff_date.date())
        triggered = [s.name for s in result.signals if s.triggered]
        results.append(DayScore(
            date=date_str,
            symbol=symbol,
            score=result.total_score,
            signals=triggered,
        ))

    return results
