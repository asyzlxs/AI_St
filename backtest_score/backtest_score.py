"""
基于历史得分的回溯分析（新信号版）。

触发模式（--mode）:
  first_cross  仅在得分从 <threshold 首次穿越到 >=threshold 时触发（默认）
  cooldown     得分 >= threshold 且距上次触发 >= cooldown 个交易日时触发

新增：
  - benchmark（沪深300）和 sector_dfs（同行业股票池）在回测中正确传入，
    使 RS 和行业动量信号在历史回测中也能生效。
  - 默认分档 20,30,40,50,60,70（每 10 分一档）
"""

import argparse
import multiprocessing
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date as date_type
from typing import List, Dict, Optional, Tuple

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from stock_cli.cache import load_cache, CACHE_DIR
from stock_cli.screener import load_symbols_from_file
from stock_cli.sector_cache import get_sector
from score_history import compute_score_history

# ─── 多进程全局状态（子进程通过 initializer 注入）────────────────────────────
_worker_benchmark: Optional["pd.Series"] = None
_worker_sector_dfs: Optional[Dict[str, "pd.DataFrame"]] = None
_worker_threshold: int = 20
_worker_horizons: List[int] = [10, 20, 30]
_worker_cooldown: int = 20
_worker_mode: str = "first_cross"


def _worker_init(project_root, benchmark, sector_dfs, threshold, horizons, cooldown, mode):
    """子进程初始化：注入 sys.path 和共享状态。"""
    global _worker_benchmark, _worker_sector_dfs
    global _worker_threshold, _worker_horizons, _worker_cooldown, _worker_mode
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if os.path.join(project_root, "backtest_score") not in sys.path:
        sys.path.insert(0, os.path.join(project_root, "backtest_score"))
    _worker_benchmark = benchmark
    _worker_sector_dfs = sector_dfs
    _worker_threshold = threshold
    _worker_horizons = horizons
    _worker_cooldown = cooldown
    _worker_mode = mode


def _worker_task(symbol: str) -> List["TriggerEvent"]:
    """子进程任务函数，直接使用进程全局状态。"""
    try:
        return collect_triggers(
            symbol,
            _worker_threshold,
            _worker_horizons,
            _worker_cooldown,
            _worker_mode,
            _worker_benchmark,
            _worker_sector_dfs,
        )
    except Exception:
        return []


# ─── 数据结构 ────────────────────────────────────────────────────────────────

@dataclass
class TriggerEvent:
    symbol: str
    trigger_date: str
    trigger_score: int
    trigger_price: float
    returns: Dict[int, Optional[float]] = field(default_factory=dict)


@dataclass
class ScoreBucket:
    label: str
    min_score: int
    count: int
    horizons: Dict[int, Optional[dict]] = field(default_factory=dict)


# ─── 基准数据加载 ─────────────────────────────────────────────────────────────

def _load_benchmark() -> Optional[pd.Series]:
    """加载沪深300历史收盘价作为 RS 基准，失败返回 None。"""
    try:
        import akshare as ak
        df = ak.stock_zh_index_daily(symbol="sh000300")
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date").sort_index()["close"]
    except Exception as e:
        print(f"[警告] 沪深300基准加载失败: {e}，RS 信号将不触发")
        return None


# ─── 触发事件收集 ─────────────────────────────────────────────────────────────

def _get_future_return(df: pd.DataFrame, trigger_idx: int, horizon: int) -> Optional[float]:
    target_idx = trigger_idx + horizon
    if target_idx >= len(df):
        return None
    price_now = float(df["Close"].iloc[trigger_idx])
    price_future = float(df["Close"].iloc[target_idx])
    if price_now <= 0:
        return None
    return (price_future - price_now) / price_now * 100.0


def collect_triggers(
    symbol: str,
    threshold: int,
    horizons: List[int],
    cooldown: int,
    mode: str,
    benchmark: Optional[pd.Series],
    sector_dfs: Optional[Dict[str, pd.DataFrame]],
) -> List[TriggerEvent]:
    """
    收集单只股票的所有触发事件。
    benchmark 和 sector_dfs 传入 compute_score_history，确保 RS/行业动量正确计算。
    """
    history = compute_score_history(
        symbol,
        benchmark=benchmark,
        sector_dfs=sector_dfs,
    )
    if not history:
        return []

    df = load_cache(symbol)
    if df.empty:
        return []
    df = df.sort_index()

    date_to_idx: Dict[str, int] = {
        str(d.date()): i for i, d in enumerate(df.index)
    }

    events: List[TriggerEvent] = []
    last_trigger_idx: Optional[int] = None

    for i, day in enumerate(history):
        if day.score < threshold:
            continue

        trigger_idx = date_to_idx.get(day.date)
        if trigger_idx is None:
            continue

        if mode == "first_cross":
            prev_score = history[i - 1].score if i > 0 else 0
            if prev_score >= threshold:
                continue
        else:
            if last_trigger_idx is not None and trigger_idx - last_trigger_idx < cooldown:
                continue

        trigger_price = float(df["Close"].iloc[trigger_idx])
        returns = {n: _get_future_return(df, trigger_idx, n) for n in horizons}

        events.append(TriggerEvent(
            symbol=symbol,
            trigger_date=day.date,
            trigger_score=day.score,
            trigger_price=trigger_price,
            returns=returns,
        ))
        last_trigger_idx = trigger_idx

    return events


# ─── 统计汇总 ─────────────────────────────────────────────────────────────────

def aggregate_by_score(
    all_events: List[TriggerEvent],
    score_thresholds: List[int],
    horizons: List[int],
) -> List[ScoreBucket]:
    buckets = []
    for thresh in sorted(score_thresholds):
        filtered = [e for e in all_events if e.trigger_score >= thresh]
        horizon_stats: Dict[int, Optional[dict]] = {}
        for n in horizons:
            vals = [e.returns[n] for e in filtered if e.returns.get(n) is not None]
            if not vals:
                horizon_stats[n] = None
                continue
            wins = sum(1 for v in vals if v > 0)
            horizon_stats[n] = {
                "count": len(vals),
                "mean": sum(vals) / len(vals),
                "median": sorted(vals)[len(vals) // 2],
                "win_rate": wins / len(vals) * 100,
                "max": max(vals),
                "min": min(vals),
            }
        buckets.append(ScoreBucket(
            label=f">={thresh}",
            min_score=thresh,
            count=len(filtered),
            horizons=horizon_stats,
        ))
    return buckets


# ─── 行业分组（用于 sector_dfs） ──────────────────────────────────────────────

def _build_sector_groups(
    symbols: List[str],
    all_dfs: Dict[str, pd.DataFrame],
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """按 sector 分组，返回 {sector: {symbol: df}}，供行业动量计算用。"""
    grouped: Dict[str, Dict[str, pd.DataFrame]] = {}
    for sym in symbols:
        if sym not in all_dfs:
            continue
        sector = get_sector(sym)
        grouped.setdefault(sector, {})[sym] = all_dfs[sym]
    return grouped


# ─── 并发回测 ─────────────────────────────────────────────────────────────────

def _precompute_all_industry_series(
    symbols: List[str],
    all_dfs: Dict[str, pd.DataFrame],
    period: int = 20,
) -> Dict[str, Optional[pd.Series]]:
    """
    主进程一次性预算每只股票的行业动量 Series。
    按 sector 分组，对每只 symbol 用同 sector 其他股票算 rolling 均涨幅。
    返回 {symbol: Series}，无 peer 时值为 None。
    """
    from stock_cli.sector_cache import get_sector as _get_sector

    # 1. 获取所有 symbol 的 sector
    sector_map: Dict[str, str] = {sym: _get_sector(sym) for sym in symbols if sym in all_dfs}

    # 2. 按 sector 分组
    sector_groups: Dict[str, List[str]] = {}
    for sym, sec in sector_map.items():
        sector_groups.setdefault(sec, []).append(sym)

    # 3. 对每个 sector，预算行业动量 Series（排除自身）
    result: Dict[str, Optional[pd.Series]] = {}
    for sec, members in sector_groups.items():
        if len(members) < 2:
            for sym in members:
                result[sym] = None
            continue

        # 所有 peer 的 rolling period 日涨幅
        peer_rets = []
        for sym in members:
            close = all_dfs[sym]["Close"].dropna()
            if len(close) < period + 1:
                continue
            peer_rets.append(close / close.shift(period) - 1)

        if not peer_rets:
            for sym in members:
                result[sym] = None
            continue

        combined = pd.concat(peer_rets, axis=1)
        sector_mean = combined.mean(axis=1)  # 全 sector 均值

        for sym in members:
            # 排除自身：sector_mean - (self_ret / n_peers)
            close = all_dfs[sym]["Close"].dropna()
            if len(close) < period + 1:
                result[sym] = sector_mean
                continue
            n = len(peer_rets)
            self_ret = close / close.shift(period) - 1
            # 去掉自身贡献：(sum - self) / (n-1)
            without_self = (sector_mean * n - self_ret) / (n - 1) if n > 1 else sector_mean
            result[sym] = without_self

    return result


def run_backtest(
    symbols: List[str],
    threshold: int,
    horizons: List[int],
    cooldown: int,
    score_thresholds: List[int],
    mode: str = "first_cross",
    max_workers: int = 8,
    label: str = "",
    use_industry: Optional[bool] = True,
) -> Tuple[List[TriggerEvent], List[ScoreBucket]]:
    tag = f"[{label}]" if label else "[回测]"
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # 1. 加载基准（一次）
    print(f"{tag} 加载沪深300基准数据...")
    benchmark = _load_benchmark()

    # 2. 并发加载所有股票全量缓存（IO 密集，用多线程）
    print(f"{tag} 并发加载股票缓存数据（{max_workers} 线程）...")
    all_dfs: Dict[str, pd.DataFrame] = {}
    _lock = threading.Lock()
    loaded = [0]

    def _load_one(sym):
        df = load_cache(sym)
        if not df.empty:
            with _lock:
                all_dfs[sym] = df.sort_index()
                loaded[0] += 1
                if loaded[0] % 200 == 0:
                    print(f"\r  {tag} 已加载 {loaded[0]}/{len(symbols)}", end="", flush=True)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_load_one, symbols))
    print(f"\r  {tag} 缓存加载完成，共 {len(all_dfs)} 只" + " " * 20)

    # 3. 主进程预算每只股票的行业动量 Series（一次性，避免子进程重复计算）
    symbol_industry_series: Dict[str, Optional[pd.Series]] = {}
    if use_industry:
        print(f"{tag} 预算行业动量序列...")
        symbol_industry_series = _precompute_all_industry_series(symbols, all_dfs)
        triggered_count = sum(1 for v in symbol_industry_series.values() if v is not None)
        print(f"  {tag} 行业动量预算完成，{triggered_count}/{len(symbols)} 只有效 peer")
    else:
        print(f"{tag} 跳过行业动量（--no-industry）")

    print(f"{tag} 共 {len(symbols)} 只股票  模式={mode}  阈值={threshold}  统计周期={horizons}天")
    print(f"  使用 multiprocessing，{max_workers} 进程并发（真正多核）")

    # 4. 构建任务列表，每个任务只含轻量参数
    valid_symbols = [s for s in symbols if s in all_dfs]
    tasks = [
        (sym, threshold, horizons, cooldown, mode,
         benchmark, symbol_industry_series.get(sym))
        for sym in valid_symbols
    ]

    # 5. multiprocessing Pool（真正多核，绕过 GIL）
    all_events: List[TriggerEvent] = []
    total = len(tasks)
    done = 0

    with multiprocessing.Pool(
        processes=max_workers,
        initializer=_mp_init,
        initargs=(project_root,),
    ) as pool:
        for events in pool.imap_unordered(_mp_task, tasks, chunksize=4):
            all_events.extend(events)
            done += 1
            print(f"\r  {tag} 进度 {done}/{total}", end="", flush=True)

    print(f"\r  {tag} 完成，共找到 {len(all_events)} 次触发事件" + " " * 20)

    buckets = aggregate_by_score(all_events, score_thresholds, horizons)
    return all_events, buckets


def _mp_init(project_root: str):
    """multiprocessing 子进程初始化，注入 sys.path。"""
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    bp = os.path.join(project_root, "backtest_score")
    if bp not in sys.path:
        sys.path.insert(0, bp)


def _mp_task(args: tuple) -> List[TriggerEvent]:
    """multiprocessing 子进程任务函数。"""
    sym, threshold, horizons, cooldown, mode, benchmark, industry_series = args
    try:
        from score_history import compute_score_history
        from stock_cli.cache import load_cache

        history = compute_score_history(
            sym,
            benchmark=benchmark,
            industry_mom_series=industry_series,
        )
        if not history:
            return []

        df = load_cache(sym)
        if df.empty:
            return []
        df = df.sort_index()

        date_to_idx = {str(d.date()): i for i, d in enumerate(df.index)}
        events = []
        last_trigger_idx = None

        for i, day in enumerate(history):
            if day.score < threshold:
                continue
            trigger_idx = date_to_idx.get(day.date)
            if trigger_idx is None:
                continue
            if mode == "first_cross":
                prev_score = history[i - 1].score if i > 0 else 0
                if prev_score >= threshold:
                    continue
            else:
                if last_trigger_idx is not None and trigger_idx - last_trigger_idx < cooldown:
                    continue

            price = float(df["Close"].iloc[trigger_idx])
            returns = {}
            for n in horizons:
                ti = trigger_idx + n
                if ti < len(df):
                    p0, p1 = float(df["Close"].iloc[trigger_idx]), float(df["Close"].iloc[ti])
                    returns[n] = (p1 - p0) / p0 * 100.0 if p0 > 0 else None
                else:
                    returns[n] = None

            events.append(TriggerEvent(
                symbol=sym, trigger_date=day.date,
                trigger_score=day.score, trigger_price=price,
                returns=returns,
            ))
            last_trigger_idx = trigger_idx

        return events
    except Exception:
        return []


# ─── 终端输出 ─────────────────────────────────────────────────────────────────

def print_summary(buckets: List[ScoreBucket], horizons: List[int], label: str = ""):
    title = f"  回测结果: {label}" if label else "  回测结果"
    col_w = 11
    sep_len = 16 + 10 + len(horizons) * col_w * 3 + 6
    sep = "=" * sep_len

    header = f"  {'得分区间':<16}{'触发次数':<10}"
    for n in horizons:
        header += f"{str(n)+'天均涨幅':>{col_w}}{str(n)+'天胜率':>{col_w}}{str(n)+'天样本':>{col_w}}"

    print(f"\n{sep}")
    print(title)
    print(sep)
    print(header)
    print("-" * sep_len)

    for b in buckets:
        row = f"  {b.label:<16}{b.count:<10}"
        for n in horizons:
            stats = b.horizons.get(n)
            if stats:
                mean_str = f"{stats['mean']:>+.2f}%"
                wr_str = f"{stats['win_rate']:.1f}%"
                row += f"{mean_str:>{col_w}}{wr_str:>{col_w}}{stats['count']:>{col_w}}"
            else:
                row += f"{'N/A':>{col_w}}{'N/A':>{col_w}}{'N/A':>{col_w}}"
        print(row)

    print(sep)

    for b in buckets:
        print(f"\n  [ {b.label}，共 {b.count} 次触发 ]")
        for n in horizons:
            stats = b.horizons.get(n)
            if not stats:
                print(f"    {n:>3}天后: 数据不足")
                continue
            print(
                f"    {n:>3}天后: "
                f"均涨幅={stats['mean']:>+.2f}%  "
                f"胜率={stats['win_rate']:.1f}%  "
                f"中位数={stats['median']:>+.2f}%  "
                f"最大={stats['max']:>+.2f}%  "
                f"最小={stats['min']:>+.2f}%  "
                f"样本={stats['count']}"
            )


# ─── Excel 导出 ───────────────────────────────────────────────────────────────

def export_excel(
    all_events: List[TriggerEvent],
    buckets: List[ScoreBucket],
    horizons: List[int],
    output_path: str,
    pool_label: str = "",
):
    summary_rows = []
    for b in buckets:
        row: dict = {"得分区间": b.label, "触发次数": b.count}
        for n in horizons:
            stats = b.horizons.get(n)
            if stats:
                row[f"{n}天均涨幅(%)"] = round(stats["mean"], 2)
                row[f"{n}天胜率(%)"] = round(stats["win_rate"], 1)
                row[f"{n}天中位数(%)"] = round(stats["median"], 2)
                row[f"{n}天最大(%)"] = round(stats["max"], 2)
                row[f"{n}天最小(%)"] = round(stats["min"], 2)
                row[f"{n}天样本数"] = stats["count"]
            else:
                for suffix in ["均涨幅(%)", "胜率(%)", "中位数(%)", "最大(%)", "最小(%)", "样本数"]:
                    row[f"{n}天{suffix}"] = None
        summary_rows.append(row)
    df_summary = pd.DataFrame(summary_rows)

    event_rows = []
    for e in sorted(all_events, key=lambda x: (x.trigger_date, x.symbol)):
        row = {
            "股票代码": e.symbol,
            "触发日期": e.trigger_date,
            "触发得分": e.trigger_score,
            "触发价格": round(e.trigger_price, 2),
        }
        for n in horizons:
            v = e.returns.get(n)
            row[f"{n}天涨幅(%)"] = round(v, 2) if v is not None else None
        event_rows.append(row)
    df_events = pd.DataFrame(event_rows)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="汇总统计", index=False)
        df_events.to_excel(writer, sheet_name="触发事件明细", index=False)

    tag = f"[{pool_label}]" if pool_label else "[输出]"
    print(f"{tag} Excel 已保存: {output_path}")


# ─── 股票池加载 ───────────────────────────────────────────────────────────────

def _load_pool_from_cache_by_market(market: str) -> List[str]:
    symbols = []
    for f in sorted(CACHE_DIR.iterdir()):
        if f.suffix != ".csv":
            continue
        parts = f.stem.rsplit("_", 1)
        if len(parts) == 2 and parts[1] == market:
            symbols.append(f"{parts[0]}.{market}")
    return symbols


BUILTIN_POOL_FILES = {
    "cyb":   "stock_cli/data/cyb.txt",
    "sgt":   "stock_cli/data/sgt.txt",
    "hs300": "stock_cli/data/hs300.txt",
    "sz50":  "stock_cli/data/sz50.txt",
}


def load_pool(pool_key: str, project_root: str) -> Tuple[List[str], str]:
    if pool_key == "hgt":
        return _load_pool_from_cache_by_market("SS"), "hgt(沪市A股)"

    if pool_key in BUILTIN_POOL_FILES:
        fpath = os.path.join(project_root, BUILTIN_POOL_FILES[pool_key])
        if os.path.exists(fpath):
            name_map = {"cyb": "创业板", "sgt": "深市A股", "hs300": "沪深300", "sz50": "上证50"}
            return load_symbols_from_file(fpath), f"{pool_key}({name_map.get(pool_key, pool_key)})"
        print(f"[警告] 找不到内置池文件: {fpath}")
        return [], pool_key

    if os.path.exists(pool_key):
        return load_symbols_from_file(pool_key), os.path.basename(pool_key)

    print(f"[警告] 未知股票池: {pool_key}")
    return [], pool_key


# ─── CLI 入口 ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="基于历史得分的股票回溯分析（新信号版：RS/行业动量/CMF）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python backtest_score.py --pools cyb
  python backtest_score.py --pools cyb,hgt,sgt
  python backtest_score.py --pools hs300 --mode cooldown --cooldown 20
        """,
    )
    parser.add_argument("--pools", type=str, default="cyb",
                        help="股票池，逗号分隔（cyb/hgt/sgt/hs300/sz50 或文件路径，默认 cyb）")
    parser.add_argument("--mode", choices=["first_cross", "cooldown"], default="first_cross",
                        help="触发模式（默认 first_cross）")
    parser.add_argument("--threshold", type=int, default=20,
                        help="触发阈值，得分 >= 该值才记录（默认20，建议低于分档最小值）")
    parser.add_argument("--cooldown", type=int, default=20,
                        help="cooldown 模式冷却交易日数（默认20）")
    parser.add_argument("--horizons", type=str, default="10,20,30",
                        help="统计收益的未来天数，逗号分隔（默认10,20,30）")
    parser.add_argument("--score-thresholds", type=str, default="20,30,40,50,60,70",
                        help="汇总报告得分分档，逗号分隔（默认20,30,40,50,60,70）")
    parser.add_argument("--workers", type=int, default=8, help="并发线程数（默认8）")
    parser.add_argument("--no-industry", action="store_true",
                        help="跳过行业动量预算（默认启用）")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Excel 输出目录（默认 output/）")
    args = parser.parse_args()

    horizons = [int(x.strip()) for x in args.horizons.split(",")]
    score_thresholds = sorted(set(int(x.strip()) for x in args.score_thresholds.split(",")))
    pool_keys = [x.strip() for x in args.pools.split(",")]
    use_industry = False if args.no_industry else True

    project_root = os.path.join(os.path.dirname(__file__), "..")
    output_dir = args.output_dir or os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)

    today = date_type.today().strftime("%Y%m%d")

    for pool_key in pool_keys:
        symbols, label = load_pool(pool_key, project_root)
        if not symbols:
            print(f"[跳过] {pool_key}：股票池为空")
            continue

        print(f"\n{'='*60}")
        print(f"  股票池: {label}  ({len(symbols)} 只)")
        print(f"{'='*60}")

        all_events, buckets = run_backtest(
            symbols=symbols,
            threshold=args.threshold,
            horizons=horizons,
            cooldown=args.cooldown,
            score_thresholds=score_thresholds,
            mode=args.mode,
            max_workers=args.workers,
            label=label,
            use_industry=use_industry,
        )

        print_summary(buckets, horizons, label=label)

        if not all_events:
            print(f"[{label}] 未找到触发事件，跳过导出")
            continue

        safe_key = pool_key.replace("/", "_").replace("\\", "_").replace(".", "_")
        output_path = os.path.join(output_dir, f"backtest_{safe_key}_{today}.xlsx")
        export_excel(all_events, buckets, horizons, output_path, pool_label=label)


if __name__ == "__main__":
    main()
