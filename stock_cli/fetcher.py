import yfinance as yf
import pandas as pd


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
