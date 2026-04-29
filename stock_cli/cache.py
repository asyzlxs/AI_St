"""
本地 CSV 缓存模块。

缓存目录: ~/.stock_cli/cache/
文件命名: symbol.replace(".", "_") + ".csv"
CSV 格式: Date,Open,High,Low,Close,Volume,Adj Close，日期升序，UTF-8 无 BOM
"""

import warnings
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).parent / "data" / "cache"
# 连续空缺超过此天数才 warn（避免周末/节假日误报）
GAP_THRESHOLD_DAYS = 7
CSV_COLUMNS = ["Open", "High", "Low", "Close", "Volume", "Adj Close"]


def _symbol_to_filename(symbol: str) -> str:
    """'300661.SZ' -> '300661_SZ.csv'"""
    return symbol.replace(".", "_") + ".csv"


def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / _symbol_to_filename(symbol)


def ensure_cache_dir():
    """创建缓存目录（幂等）。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_cache(symbol: str) -> pd.DataFrame:
    """读取指定 symbol 的全量缓存，返回 DataFrame（Date 为 DatetimeIndex）。
    文件不存在时返回空 DataFrame。
    """
    path = _cache_path(symbol)
    if not path.exists():
        return _empty_df()

    try:
        df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
        df.index = df.index.tz_localize(None)
        # 补齐缺失列（兼容旧缓存）
        for col in CSV_COLUMNS:
            if col not in df.columns:
                df[col] = float("nan")
        return df.sort_index()
    except Exception as e:
        warnings.warn(f"[cache] 读取 {symbol} 缓存失败，将重新获取: {e}")
        return _empty_df()


def _empty_df() -> pd.DataFrame:
    df = pd.DataFrame(columns=CSV_COLUMNS)
    df.index.name = "Date"
    return df


def save_cache(symbol: str, df: pd.DataFrame):
    """将 df 合并写入缓存文件（read-modify-write，新数据覆盖旧数据）。
    df 的 index 须为 DatetimeIndex（同 fetcher 返回格式）。
    """
    if df.empty:
        return

    # 过滤掉价格列全为 NaN 的行（如当天数据未就绪时 yfinance 返回的空行）
    price_cols = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]
    if price_cols:
        df = df.dropna(subset=price_cols, how="all")
    if df.empty:
        return

    ensure_cache_dir()
    existing = load_cache(symbol)

    if existing.empty:
        merged = df.copy()
    else:
        merged = pd.concat([existing, df])
        merged = merged[~merged.index.duplicated(keep="last")]

    merged = merged.sort_index()

    # 只写标准列
    cols_to_write = [c for c in CSV_COLUMNS if c in merged.columns]
    out = merged[cols_to_write].copy()
    out.index.name = "Date"

    path = _cache_path(symbol)
    out.to_csv(path, date_format="%Y-%m-%d")


def slice_cache(symbol: str, start: str, end: str) -> pd.DataFrame:
    """从缓存取 [start, end] 区间数据（端点均包含）。
    返回空 DataFrame 表示完全无缓存。
    """
    df = load_cache(symbol)
    if df.empty:
        return df
    return df.loc[start:end]


def check_cache_coverage(symbol: str, start: str, end: str) -> bool:
    """检查缓存对 [start, end] 的覆盖情况，不足时输出 warning。

    返回 True：覆盖充分（可能有节假日空洞但不视为缺失）。
    返回 False：有明确的头部或尾部数据缺失。
    """
    df = slice_cache(symbol, start, end)

    if df.empty:
        warnings.warn(
            f"[cache] {symbol}: 无本地缓存数据（{start} ~ {end}），"
            "建议运行 `stock update-cache` 更新缓存"
        )
        return False

    cache_start = str(df.index.min().date())
    cache_end = str(df.index.max().date())
    sufficient = True

    if cache_end < end:
        warnings.warn(
            f"[cache] {symbol}: 缓存最新日期 {cache_end}，请求截止 {end}，"
            "尾部数据缺失，建议运行 `stock update-cache`"
        )
        sufficient = False

    if cache_start > start:
        warnings.warn(
            f"[cache] {symbol}: 缓存最早日期 {cache_start}，请求起始 {start}，"
            "头部数据缺失，建议运行 `stock update-cache --start {start}`"
        )
        sufficient = False

    if sufficient:
        # 检查内部空洞（仅 warn，不改变 sufficient，可能是节假日）
        for gap_start, gap_end, gap_days in _detect_internal_gaps(df):
            warnings.warn(
                f"[cache] {symbol}: {gap_start} ~ {gap_end} "
                f"有 {gap_days} 天连续缺口（可能是节假日）"
            )

    return sufficient


def _detect_internal_gaps(df: pd.DataFrame) -> list:
    """找出超过 GAP_THRESHOLD_DAYS 的相邻日期空洞。
    返回 [(gap_start_str, gap_end_str, days), ...]
    """
    if len(df) < 2:
        return []
    gaps = []
    dates = df.index.sort_values()
    for i in range(1, len(dates)):
        delta = (dates[i] - dates[i - 1]).days
        if delta > GAP_THRESHOLD_DAYS:
            gaps.append((
                str(dates[i - 1].date()),
                str(dates[i].date()),
                delta,
            ))
    return gaps
