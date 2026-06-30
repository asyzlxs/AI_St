"""
行业分类缓存预取脚本（一次性执行）

从 stock_cli/data/cache/ 读取所有已缓存股票代码，
并发通过 yfinance 拉取 sector，写入 stock_cli/data/sector_map.json。

已有记录的股票自动跳过，只拉取缺失的。

用法:
    python update_sector_cache.py              # 默认 16 线程
    python update_sector_cache.py --workers 32
    python update_sector_cache.py --force      # 强制重新拉取所有（忽略已有缓存）
"""

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yfinance as yf

CACHE_DIR = Path(__file__).parent / "stock_cli" / "data" / "cache"
SECTOR_FILE = Path(__file__).parent / "stock_cli" / "data" / "sector_map.json"

_lock = threading.Lock()


def all_cached_symbols() -> list:
    """从缓存目录推导所有股票代码。"""
    symbols = []
    for f in sorted(CACHE_DIR.iterdir()):
        if f.suffix != ".csv":
            continue
        parts = f.stem.rsplit("_", 1)
        if len(parts) == 2:
            symbols.append(f"{parts[0]}.{parts[1]}")
    return symbols


def load_existing(force: bool) -> dict:
    if force or not SECTOR_FILE.exists():
        return {}
    try:
        with open(SECTOR_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(data: dict):
    SECTOR_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SECTOR_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_one(symbol: str) -> tuple:
    """拉取单只股票的 sector，失败返回 'Unknown'。"""
    for attempt in range(2):
        try:
            info = yf.Ticker(symbol).info
            sector = info.get("sector") or "Unknown"
            return symbol, sector
        except Exception:
            if attempt == 0:
                time.sleep(1)
    return symbol, "Unknown"


def main():
    parser = argparse.ArgumentParser(description="预取所有缓存股票的行业分类")
    parser.add_argument("--workers", type=int, default=8, help="并发线程数（默认8）")
    parser.add_argument("--force", action="store_true", help="忽略已有缓存，强制重新拉取全部")
    args = parser.parse_args()

    all_symbols = all_cached_symbols()
    data = load_existing(args.force)

    missing = [s for s in all_symbols if s not in data]

    print(f"缓存股票总数  : {len(all_symbols)}")
    print(f"已有 sector  : {len(data)}")
    print(f"待拉取        : {len(missing)}")

    if not missing:
        print("所有股票已有 sector 缓存，无需拉取。")
        return

    print(f"开始并发拉取（{args.workers} 线程）...\n")

    done = 0
    failed = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_one, sym): sym for sym in missing}
        for future in as_completed(futures):
            symbol, sector = future.result()
            done += 1
            if sector == "Unknown":
                failed += 1

            with _lock:
                data[symbol] = sector
                # 每 200 条写一次磁盘，防止中断丢失进度
                if done % 200 == 0:
                    save(data)

            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 else 0
            eta = (len(missing) - done) / rate if rate > 0 else 0
            print(
                f"\r  进度: {done}/{len(missing)}  "
                f"失败: {failed}  "
                f"速度: {rate:.1f}/s  "
                f"预计剩余: {eta:.0f}s    ",
                end="", flush=True,
            )

    # 最终写入
    save(data)

    elapsed = time.time() - start_time
    print(f"\n\n完成！")
    print(f"  总耗时  : {elapsed:.1f}s")
    print(f"  成功    : {done - failed}")
    print(f"  Unknown : {failed}（A股部分 yfinance 无 sector 数据属正常）")
    print(f"  文件    : {SECTOR_FILE}")

    # 打印 sector 分布
    from collections import Counter
    dist = Counter(data.values())
    print(f"\nSector 分布（前10）:")
    for sector, count in dist.most_common(10):
        print(f"  {sector:<40} {count}")


if __name__ == "__main__":
    main()
