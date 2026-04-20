import os
import json
import yfinance as yf
import pandas as pd
import akshare as ak

# A股代码-名称映射表缓存（懒加载）
_a_stock_name_cache = None


def _get_a_stock_name_cache():
    """获取 A 股代码-名称映射表（优先从本地缓存文件读取，失败则在线获取）。"""
    global _a_stock_name_cache
    if _a_stock_name_cache is None:
        # 1. 尝试从本地 JSON 文件读取（无需外网 VPN）
        cache_file = os.path.join(os.path.dirname(__file__), "data", "a_stock_names.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    _a_stock_name_cache = json.load(f)
                return _a_stock_name_cache
            except Exception:
                pass
                
        # 2. 如果本地读取失败或文件不存在，退回到在线获取
        try:
            # 获取沪深京所有股票的代码和名称
            df = ak.stock_info_a_code_name()
            # 创建代码到名称的映射字典
            _a_stock_name_cache = dict(zip(df['code'], df['name']))
        except Exception:
            _a_stock_name_cache = {}
    return _a_stock_name_cache


def fetch_stock_name(symbol: str) -> str:
    """获取股票名称。

    Args:
        symbol: 股票代码 (如 AAPL, 600519.SS, 7203.T)

    Returns:
        股票名称，如果获取失败则返回空字符串
    """
    try:
        # 对于 A 股（.SS 上证, .SZ 深证），使用 akshare 获取中文名称
        if symbol.endswith('.SS') or symbol.endswith('.SZ'):
            # 提取纯数字代码（去掉 .SS/.SZ 后缀）
            code = symbol.split('.')[0]
            cache = _get_a_stock_name_cache()
            name = cache.get(code, '')
            if name:
                return name

        # 对于其他市场或查询失败，使用 yfinance
        ticker = yf.Ticker(symbol)
        info = ticker.info
        name = info.get('longName') or info.get('shortName') or ''
        return name
    except Exception:
        return ''


def fetch_stock_data(symbol: str, start: str, end: str) -> pd.DataFrame:
    """获取股票历史数据。

    Args:
        symbol: 股票代码 (如 AAPL, 600519.SS, 7203.T)
        start: 开始日期 YYYY-MM-DD
        end: 结束日期 YYYY-MM-DD

    Returns:
        包含 OHLCV 数据的 DataFrame
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end)

    if df.empty:
        raise ValueError(f"未获取到 {symbol} 在 {start} ~ {end} 的数据，请检查股票代码或时间范围")

    df.index = df.index.tz_localize(None)
    df.index.name = "Date"
    return df
