"""
基于历史得分的回溯分析。

触发模式（--mode）:
  first_cross  仅在得分从 <threshold 首次穿越到 >=threshold 时触发（默认）
  cooldown     得分 >= threshold 且距上次触发 >= cooldown 个交易日时触发

流程:
1. 遍历股票池，对每只股票计算全部历史每日得分
2. 按触发模式收集触发事件
3. 统计触发后 N 天的收益率分布
4. 按得分分档汇总（含10/20天胜率）
5. 输出终端表格 + Excel 报告
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date as date_type
from typing import List, Dict, Optional, Tuple

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from stock_cli.cache import load_cache, CACHE_DIR
from stock_cli.screener import load_symbols_from_file
from score_history import compute_score_history


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
    mode: str,  # "first_cross" | "cooldown"
) -> List[TriggerEvent]:
    """
    收集单只股票的所有触发事件。

    first_cross 模式：前一天得分 < threshold 且当天得分 >= threshold，才记录
    cooldown 模式：得分 >= threshold，且距上次触发 >= cooldown 个交易日
    """
    history = compute_score_history(symbol)
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
            # 前一条历史记录的得分必须 < threshold（即首次穿越）
            prev_score = history[i - 1].score if i > 0 else 0
            if prev_score >= threshold:
                continue
        else:
            # cooldown 模式
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


# ─── 并发回测 ─────────────────────────────────────────────────────────────────

def run_backtest(
    symbols: List[str],
    threshold: int,
    horizons: List[int],
    cooldown: int,
    score_thresholds: List[int],
    mode: str = "first_cross",
    max_workers: int = 8,
    label: str = "",
) -> Tuple[List[TriggerEvent], List[ScoreBucket]]:
    all_events: List[TriggerEvent] = []
    total = len(symbols)
    done = 0

    tag = f"[{label}]" if label else "[回测]"
    print(f"{tag} 共 {total} 只股票  模式={mode}  阈值={threshold}  统计周期={horizons}天")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(collect_triggers, sym, threshold, horizons, cooldown, mode): sym
            for sym in symbols
        }
        for future in as_completed(futures):
            sym = futures[future]
            done += 1
            try:
                events = future.result()
                all_events.extend(events)
            except Exception as e:
                pass
            print(f"\r  {tag} 进度 {done}/{total}", end="", flush=True)

    print(f"\r  {tag} 完成，共找到 {len(all_events)} 次触发事件" + " " * 20)

    buckets = aggregate_by_score(all_events, score_thresholds, horizons)
    return all_events, buckets


# ─── 终端输出 ─────────────────────────────────────────────────────────────────

def print_summary(buckets: List[ScoreBucket], horizons: List[int], label: str = ""):
    title = f"  回测结果: {label}" if label else "  回测结果"
    # 动态列宽
    col_w = 11
    n_cols = 1 + 1 + len(horizons) * 3  # 区间 + 次数 + (均涨幅+10天胜率+20天胜率) * horizons
    # 简化：每个horizon输出3列：均涨幅、胜率、样本
    sep_len = 16 + 10 + len(horizons) * col_w * 3 + 6
    sep = "=" * sep_len

    header = f"  {'得分区间':<16}{'触发次数':<10}"
    for n in horizons:
        header += f"{f'{n}天均涨幅':>{col_w}}{f'{n}天胜率':>{col_w}}{f'{n}天样本':>{col_w}}"

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

    # 详细行（中位数/最大/最小）
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
    # Sheet 1: 汇总统计
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

    # Sheet 2: 原始触发事件
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
    """从缓存目录按市场后缀（SS/SZ）推导股票列表。"""
    symbols = []
    for f in sorted(CACHE_DIR.iterdir()):
        if f.suffix != ".csv":
            continue
        stem = f.stem  # "600519_SS"
        parts = stem.rsplit("_", 1)
        if len(parts) == 2 and parts[1] == market:
            symbols.append(f"{parts[0]}.{market}")
    return symbols


BUILTIN_POOL_FILES = {
    "cyb": "stock_cli/data/cyb.txt",
    "sgt": "stock_cli/data/sgt.txt",
    "hs300": "stock_cli/data/hs300.txt",
    "sz50": "stock_cli/data/sz50.txt",
}


def load_pool(pool_key: str, project_root: str) -> Tuple[List[str], str]:
    """
    加载内置或自定义股票池。
    返回 (symbols, 描述标签)。

    支持:
      cyb / sgt / hs300 / sz50  → 读取 stock_cli/data/{key}.txt
      hgt                        → 从缓存推导沪市 SS 股票
      任意文件路径               → 直接读取
    """
    if pool_key == "hgt":
        symbols = _load_pool_from_cache_by_market("SS")
        return symbols, "hgt(沪市A股)"

    if pool_key in BUILTIN_POOL_FILES:
        fpath = os.path.join(project_root, BUILTIN_POOL_FILES[pool_key])
        if os.path.exists(fpath):
            symbols = load_symbols_from_file(fpath)
            name_map = {"cyb": "创业板", "sgt": "深市A股", "hs300": "沪深300", "sz50": "上证50"}
            return symbols, f"{pool_key}({name_map.get(pool_key, pool_key)})"
        print(f"[警告] 找不到内置池文件: {fpath}")
        return [], pool_key

    # 当作文件路径
    if os.path.exists(pool_key):
        symbols = load_symbols_from_file(pool_key)
        return symbols, os.path.basename(pool_key)

    print(f"[警告] 未知股票池: {pool_key}")
    return [], pool_key


# ─── CLI 入口 ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="基于历史得分的股票回溯分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python backtest_score.py --pools cyb
  python backtest_score.py --pools cyb,hgt,sgt
  python backtest_score.py --pools hs300 --mode cooldown --cooldown 20
  python backtest_score.py --pools sgt --threshold 20 --score-thresholds 20,30,40,50,60,80
        """,
    )
    parser.add_argument(
        "--pools", type=str, default="cyb",
        help="股票池，逗号分隔，支持 cyb/hgt/sgt/hs300/sz50 或文件路径（默认 cyb）",
    )
    parser.add_argument(
        "--mode", choices=["first_cross", "cooldown"], default="first_cross",
        help="触发模式：first_cross=首次穿越阈值（默认），cooldown=冷却期模式",
    )
    parser.add_argument(
        "--threshold", type=int, default=20,
        help="触发阈值（得分 >= 该值，默认20）",
    )
    parser.add_argument(
        "--cooldown", type=int, default=20,
        help="cooldown 模式下的冷却交易日数（默认20）",
    )
    parser.add_argument(
        "--horizons", type=str, default="10,20,30",
        help="统计收益的未来天数，逗号分隔（默认10,20,30）",
    )
    parser.add_argument(
        "--score-thresholds", type=str, default="20,30,40,50,60,80",
        help="汇总报告的得分分档，逗号分隔（默认20,30,40,50,60,80）",
    )
    parser.add_argument("--workers", type=int, default=8, help="并发线程数（默认8）")
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Excel 输出目录，默认为项目根目录下的 output/",
    )
    args = parser.parse_args()

    horizons = [int(x.strip()) for x in args.horizons.split(",")]
    score_thresholds = sorted(set(int(x.strip()) for x in args.score_thresholds.split(",")))
    pool_keys = [x.strip() for x in args.pools.split(",")]

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
