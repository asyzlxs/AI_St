"""
行业分类缓存模块。

本地文件: stock_cli/data/sector_map.json
格式: {"600519.SS": "Consumer Defensive", "000858.SZ": "Consumer Defensive", ...}

逻辑:
- 本地有记录 → 直接返回
- 本地无此 symbol → 联网拉取 yfinance info，写入本地，返回
- 联网失败 → 返回 "Unknown"
"""

import json
import os
import threading
from typing import Optional

import yfinance as yf

_CACHE_FILE = os.path.join(os.path.dirname(__file__), "data", "sector_map.json")
_lock = threading.Lock()
_mem: Optional[dict] = None  # 进程内内存缓存


def _load_file() -> dict:
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_file(data: dict):
    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _ensure_loaded() -> dict:
    global _mem
    if _mem is None:
        with _lock:
            if _mem is None:
                _mem = _load_file()
    return _mem


def get_sector(symbol: str) -> str:
    """
    获取股票所属 sector。本地无记录时联网拉取并缓存。
    失败时返回 'Unknown'。
    """
    data = _ensure_loaded()

    if symbol in data:
        return data[symbol]

    # 联网拉取
    sector = "Unknown"
    try:
        info = yf.Ticker(symbol).info
        sector = info.get("sector") or "Unknown"
    except Exception:
        pass

    # 写回本地（加锁保证并发安全）
    with _lock:
        data[symbol] = sector
        _save_file(data)

    return sector


def prefetch_sectors(symbols: list, max_workers: int = 8):
    """
    批量预取行业分类，已有本地缓存的跳过，只拉取缺失的。
    供 update-cache 或首次使用时调用。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    data = _ensure_loaded()
    missing = [s for s in symbols if s not in data]
    if not missing:
        return

    print(f"[sector] 预取 {len(missing)} 只股票的行业分类（已有 {len(data)} 条本地缓存）...")
    done = 0

    def _fetch(sym):
        try:
            info = yf.Ticker(sym).info
            return sym, info.get("sector") or "Unknown"
        except Exception:
            return sym, "Unknown"

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch, s): s for s in missing}
        for future in as_completed(futures):
            sym, sector = future.result()
            done += 1
            with _lock:
                data[sym] = sector
            print(f"\r  [sector] {done}/{len(missing)}", end="", flush=True)

    with _lock:
        _save_file(data)
    print(f"\r  [sector] 完成，共缓存 {len(data)} 条" + " " * 20)
