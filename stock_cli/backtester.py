import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from stock_cli.fetcher import fetch_stock_data
from stock_cli.indicators import (
    moving_averages, detect_golden_cross, detect_bullish_alignment,
    compute_rsi, detect_rsi_oversold_bounce,
    compute_macd, detect_macd_histogram_turn_positive, detect_macd_bottom_divergence,
    detect_volume_surge, detect_price_breakout,
    compute_atr, detect_atr_squeeze_breakout,
)
from stock_cli.screener import SIGNAL_CONFIG, MAX_POSSIBLE

# CJK 字体
_CJK_FONTS = ["Heiti TC", "Hiragino Sans GB", "Arial Unicode MS", "SimHei"]
for _name in _CJK_FONTS:
    if any(f.name == _name for f in fm.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [_name] + plt.rcParams["font.sans-serif"]
        plt.rcParams["axes.unicode_minus"] = False
        break


# ────────────────────────── 数据结构 ──────────────────────────

@dataclass
class Trade:
    symbol: str
    signal_name: str
    buy_date: str
    buy_price: float
    sell_date: str
    sell_price: float
    hold_days: int
    return_pct: float
    exit_reason: str


@dataclass
class SignalBacktestResult:
    signal_name: str
    signal_label: str
    exit_rule: str
    trades: List[Trade] = field(default_factory=list)
    total_trades: int = 0
    win_rate: float = 0.0
    avg_return: float = 0.0
    max_return: float = 0.0
    max_loss: float = 0.0
    profit_factor: float = 0.0
    cumulative_return: float = 0.0


@dataclass
class BacktestReport:
    pool_name: str
    start: str
    end: str
    total_stocks: int = 0
    failed_stocks: int = 0
    signal_results: List[SignalBacktestResult] = field(default_factory=list)
    combo_results: List[SignalBacktestResult] = field(default_factory=list)
    random_results: List[SignalBacktestResult] = field(default_factory=list)


# ────────────────────────── 信号扫描 ──────────────────────────

def _precompute_indicators(df: pd.DataFrame) -> Dict:
    """一次性计算所有指标。"""
    ma_df = moving_averages(df)
    rsi = compute_rsi(df)
    macd_df = compute_macd(df)
    atr = compute_atr(df)
    return {
        "ma_df": ma_df, "rsi": rsi, "macd_df": macd_df, "atr": atr,
    }


def _check_signal_at(df: pd.DataFrame, ind: Dict, signal_name: str, i: int) -> bool:
    """检查第 i 天是否触发指定信号。ind 是预计算的指标。"""
    ma_df = ind["ma_df"]
    rsi = ind["rsi"]
    macd_df = ind["macd_df"]
    atr = ind["atr"]

    if signal_name == "golden_cross":
        return detect_golden_cross(ma_df["MA5"].iloc[:i+1], ma_df["MA20"].iloc[:i+1])
    elif signal_name == "bullish_alignment":
        return detect_bullish_alignment(
            df["Close"].iloc[:i+1], ma_df["MA5"].iloc[:i+1],
            ma_df["MA20"].iloc[:i+1], ma_df["MA60"].iloc[:i+1])
    elif signal_name == "rsi_bounce":
        return detect_rsi_oversold_bounce(rsi.iloc[:i+1])
    elif signal_name == "macd_turn":
        return detect_macd_histogram_turn_positive(macd_df["Histogram"].iloc[:i+1])
    elif signal_name == "macd_divergence":
        return detect_macd_bottom_divergence(df["Close"].iloc[:i+1], macd_df["MACD"].iloc[:i+1])
    elif signal_name == "volume_surge":
        return detect_volume_surge(df.iloc[:i+1])
    elif signal_name == "price_breakout":
        return detect_price_breakout(df.iloc[:i+1])
    elif signal_name == "atr_squeeze":
        return detect_atr_squeeze_breakout(atr.iloc[:i+1])
    return False


def run_signal_scan(df: pd.DataFrame, ind: Dict, signal_name: str) -> List[int]:
    """扫描全部交易日，返回信号触发的日期索引列表。"""
    indices = []
    start_idx = 60
    for i in range(start_idx, len(df)):
        if _check_signal_at(df, ind, signal_name, i):
            indices.append(i)
    return indices


def run_combo_scan(df: pd.DataFrame, ind: Dict, min_score: int) -> List[int]:
    """扫描全部交易日，返回综合评分 >= min_score 的日期索引列表。"""
    indices = []
    start_idx = 60
    for i in range(start_idx, len(df)):
        total = 0
        for cfg in SIGNAL_CONFIG:
            if _check_signal_at(df, ind, cfg["name"], i):
                total += cfg["max_score"]
        if total >= min_score:
            indices.append(i)
    return indices


# ────────────────────────── 交易模拟 ──────────────────────────

def simulate_trades_fixed_hold(df: pd.DataFrame, signal_indices: List[int],
                                hold_days: int, symbol: str,
                                signal_name: str) -> List[Trade]:
    """固定持仓天数策略。"""
    trades = []
    last_sell_idx = -1

    for sig_idx in signal_indices:
        buy_idx = sig_idx + 1  # 次日买入
        sell_idx = buy_idx + hold_days

        if buy_idx >= len(df) or buy_idx <= last_sell_idx:
            continue
        if sell_idx >= len(df):
            sell_idx = len(df) - 1

        buy_price = float(df["Open"].iloc[buy_idx])
        sell_price = float(df["Close"].iloc[sell_idx])
        if buy_price <= 0:
            continue

        ret = (sell_price - buy_price) / buy_price * 100
        trades.append(Trade(
            symbol=symbol, signal_name=signal_name,
            buy_date=str(df.index[buy_idx].date()),
            buy_price=buy_price,
            sell_date=str(df.index[sell_idx].date()),
            sell_price=sell_price,
            hold_days=sell_idx - buy_idx,
            return_pct=ret,
            exit_reason=f"hold_{hold_days}",
        ))
        last_sell_idx = sell_idx
    return trades


def simulate_trades_tp_sl(df: pd.DataFrame, signal_indices: List[int],
                           take_profit: float, stop_loss: float,
                           max_hold: int, symbol: str,
                           signal_name: str) -> List[Trade]:
    """止盈止损策略。"""
    trades = []
    last_sell_idx = -1

    for sig_idx in signal_indices:
        buy_idx = sig_idx + 1
        if buy_idx >= len(df) or buy_idx <= last_sell_idx:
            continue

        buy_price = float(df["Open"].iloc[buy_idx])
        if buy_price <= 0:
            continue

        tp_price = buy_price * (1 + take_profit)
        sl_price = buy_price * (1 - stop_loss)

        sell_idx = buy_idx
        sell_price = buy_price
        exit_reason = "timeout"

        for j in range(buy_idx, min(buy_idx + max_hold + 1, len(df))):
            high = float(df["High"].iloc[j])
            low = float(df["Low"].iloc[j])

            if low <= sl_price:
                sell_idx = j
                sell_price = sl_price
                exit_reason = "stop_loss"
                break
            if high >= tp_price:
                sell_idx = j
                sell_price = tp_price
                exit_reason = "take_profit"
                break
            sell_idx = j
            sell_price = float(df["Close"].iloc[j])

        ret = (sell_price - buy_price) / buy_price * 100
        trades.append(Trade(
            symbol=symbol, signal_name=signal_name,
            buy_date=str(df.index[buy_idx].date()),
            buy_price=buy_price,
            sell_date=str(df.index[sell_idx].date()),
            sell_price=sell_price,
            hold_days=sell_idx - buy_idx,
            return_pct=ret,
            exit_reason=exit_reason,
        ))
        last_sell_idx = sell_idx
    return trades


def generate_random_trades(all_dfs: Dict[str, pd.DataFrame],
                            n_trades: int, hold_days: int) -> List[Trade]:
    """随机基准：在所有股票中随机选日期买入。"""
    trades = []
    symbols = list(all_dfs.keys())
    if not symbols:
        return trades

    for _ in range(n_trades):
        symbol = random.choice(symbols)
        df = all_dfs[symbol]
        if len(df) < 80:
            continue
        max_idx = len(df) - hold_days - 2
        if max_idx <= 60:
            continue
        sig_idx = random.randint(60, max_idx)
        buy_idx = sig_idx + 1
        sell_idx = buy_idx + hold_days
        if sell_idx >= len(df):
            sell_idx = len(df) - 1

        buy_price = float(df["Open"].iloc[buy_idx])
        if buy_price <= 0:
            continue
        sell_price = float(df["Close"].iloc[sell_idx])
        ret = (sell_price - buy_price) / buy_price * 100
        trades.append(Trade(
            symbol=symbol, signal_name="random",
            buy_date=str(df.index[buy_idx].date()),
            buy_price=buy_price,
            sell_date=str(df.index[sell_idx].date()),
            sell_price=sell_price,
            hold_days=sell_idx - buy_idx,
            return_pct=ret,
            exit_reason=f"hold_{hold_days}",
        ))
    return trades


def generate_random_trades_tp_sl(all_dfs: Dict[str, pd.DataFrame],
                                  n_trades: int, take_profit: float,
                                  stop_loss: float, max_hold: int) -> List[Trade]:
    """随机基准（止盈止损版）。"""
    trades = []
    symbols = list(all_dfs.keys())
    if not symbols:
        return trades

    for _ in range(n_trades):
        symbol = random.choice(symbols)
        df = all_dfs[symbol]
        if len(df) < 80:
            continue
        max_idx = len(df) - max_hold - 2
        if max_idx <= 60:
            continue
        sig_idx = random.randint(60, max_idx)
        t = simulate_trades_tp_sl(df, [sig_idx], take_profit, stop_loss,
                                   max_hold, symbol, "random")
        trades.extend(t)
    return trades


# ────────────────────────── 统计 ──────────────────────────

def calc_stats(trades: List[Trade], signal_name: str,
                signal_label: str, exit_rule: str) -> SignalBacktestResult:
    """从交易列表计算统计指标。"""
    result = SignalBacktestResult(
        signal_name=signal_name, signal_label=signal_label, exit_rule=exit_rule)

    if not trades:
        return result

    returns = [t.return_pct for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]

    result.trades = trades
    result.total_trades = len(trades)
    result.win_rate = len(wins) / len(trades) * 100
    result.avg_return = np.mean(returns)
    result.max_return = max(returns)
    result.max_loss = min(returns)

    avg_win = np.mean(wins) if wins else 0
    avg_loss = abs(np.mean(losses)) if losses else 0.001
    result.profit_factor = avg_win / avg_loss if avg_loss > 0 else float("inf")

    cum = 1.0
    for r in returns:
        cum *= (1 + r / 100)
    result.cumulative_return = (cum - 1) * 100

    return result


# ────────────────────────── 回测主流程 ──────────────────────────

EXIT_RULES = [
    {"name": "hold_5",   "label": "持仓5天",  "type": "fixed", "hold": 5},
    {"name": "hold_10",  "label": "持仓10天", "type": "fixed", "hold": 10},
    {"name": "hold_20",  "label": "持仓20天", "type": "fixed", "hold": 20},
    {"name": "tp10_sl5", "label": "止盈10%止损5%", "type": "tp_sl",
     "tp": 0.10, "sl": 0.05, "max_hold": 20},
]

COMBO_THRESHOLDS = [20, 30, 40]


def run_backtest(symbols: List[str], start: str, end: str,
                  pool_name: str = "", random_n: int = 1000,
                  on_progress: Optional[Callable] = None) -> BacktestReport:
    """完整回测入口。"""
    report = BacktestReport(pool_name=pool_name, start=start, end=end)

    # 1. 获取所有股票数据
    all_dfs: Dict[str, pd.DataFrame] = {}
    all_inds: Dict[str, Dict] = {}
    total = len(symbols)

    for idx, symbol in enumerate(symbols, 1):
        if on_progress:
            on_progress(idx, total, symbol, "获取数据")
        try:
            df = fetch_stock_data(symbol, start, end)
            if len(df) >= 70:
                all_dfs[symbol] = df
                all_inds[symbol] = _precompute_indicators(df)
            else:
                report.failed_stocks += 1
        except Exception:
            report.failed_stocks += 1
        if idx < total:
            time.sleep(0.3)

    report.total_stocks = len(all_dfs)

    # 2. 扫描所有信号
    # signal_name -> List[int] per symbol
    signal_triggers: Dict[str, Dict[str, List[int]]] = {}
    for cfg in SIGNAL_CONFIG:
        signal_triggers[cfg["name"]] = {}

    combo_triggers: Dict[int, Dict[str, List[int]]] = {t: {} for t in COMBO_THRESHOLDS}

    for idx, (symbol, df) in enumerate(all_dfs.items(), 1):
        if on_progress:
            on_progress(idx, len(all_dfs), symbol, "扫描信号")
        ind = all_inds[symbol]
        for cfg in SIGNAL_CONFIG:
            indices = run_signal_scan(df, ind, cfg["name"])
            signal_triggers[cfg["name"]][symbol] = indices
        for threshold in COMBO_THRESHOLDS:
            combo_triggers[threshold][symbol] = run_combo_scan(df, ind, threshold)

    # 3. 模拟交易
    for exit_rule in EXIT_RULES:
        # 8 个单信号
        for cfg in SIGNAL_CONFIG:
            all_trades = []
            for symbol, indices in signal_triggers[cfg["name"]].items():
                df = all_dfs[symbol]
                if exit_rule["type"] == "fixed":
                    trades = simulate_trades_fixed_hold(
                        df, indices, exit_rule["hold"], symbol, cfg["name"])
                else:
                    trades = simulate_trades_tp_sl(
                        df, indices, exit_rule["tp"], exit_rule["sl"],
                        exit_rule["max_hold"], symbol, cfg["name"])
                all_trades.extend(trades)
            report.signal_results.append(
                calc_stats(all_trades, cfg["name"], cfg["label"], exit_rule["name"]))

        # 综合评分
        for threshold in COMBO_THRESHOLDS:
            all_trades = []
            for symbol, indices in combo_triggers[threshold].items():
                df = all_dfs[symbol]
                if exit_rule["type"] == "fixed":
                    trades = simulate_trades_fixed_hold(
                        df, indices, exit_rule["hold"], symbol, f"score>={threshold}")
                else:
                    trades = simulate_trades_tp_sl(
                        df, indices, exit_rule["tp"], exit_rule["sl"],
                        exit_rule["max_hold"], symbol, f"score>={threshold}")
                all_trades.extend(trades)
            report.combo_results.append(
                calc_stats(all_trades, f"score>={threshold}",
                           f"综合>={threshold}分", exit_rule["name"]))

        # 随机基准
        if exit_rule["type"] == "fixed":
            rand_trades = generate_random_trades(all_dfs, random_n, exit_rule["hold"])
        else:
            rand_trades = generate_random_trades_tp_sl(
                all_dfs, random_n, exit_rule["tp"], exit_rule["sl"], exit_rule["max_hold"])
        report.random_results.append(
            calc_stats(rand_trades, "random", "★ 随机买入", exit_rule["name"]))

    return report


# ────────────────────────── 报告格式化 ──────────────────────────

def _format_table(results: List[SignalBacktestResult],
                   random_result: Optional[SignalBacktestResult] = None) -> str:
    """格式化一组结果为文本表格。"""
    header = (f"  {'信号':<18} {'交易数':>6} {'胜率':>7} {'平均收益':>8} "
              f"{'最大收益':>8} {'最大亏损':>8} {'盈亏比':>6} {'累计收益':>8}")
    sep = "  " + "─" * 74
    lines = [header, sep]

    all_results = list(results)
    if random_result:
        all_results.append(random_result)

    for r in all_results:
        if r.total_trades == 0:
            lines.append(f"  {r.signal_label:<18} {'0':>6} {'--':>7} {'--':>8} "
                          f"{'--':>8} {'--':>8} {'--':>6} {'--':>8}")
        else:
            lines.append(
                f"  {r.signal_label:<18} {r.total_trades:>6} "
                f"{r.win_rate:>6.1f}% {r.avg_return:>+7.2f}% "
                f"{r.max_return:>+7.1f}% {r.max_loss:>+7.1f}% "
                f"{r.profit_factor:>6.2f} {r.cumulative_return:>+7.1f}%")
    return "\n".join(lines)


def format_backtest_report(report: BacktestReport) -> str:
    """格式化完整回测报告。"""
    lines = []
    lines.append("=" * 80)
    lines.append(f"  {report.pool_name} 回测报告 ({report.start} ~ {report.end})")
    lines.append(f"  股票数: {report.total_stocks}  失败: {report.failed_stocks}")
    lines.append("=" * 80)

    n_signals = len(SIGNAL_CONFIG)
    n_combos = len(COMBO_THRESHOLDS)

    for rule_idx, exit_rule in enumerate(EXIT_RULES):
        lines.append(f"\n  === {exit_rule['label']} ===\n")

        # 单信号结果
        sig_results = report.signal_results[rule_idx * n_signals:(rule_idx + 1) * n_signals]
        rand_result = report.random_results[rule_idx]
        lines.append(_format_table(sig_results, rand_result))

        # 综合评分
        combo_start = rule_idx * n_combos
        combo_slice = report.combo_results[combo_start:combo_start + n_combos]
        if combo_slice:
            lines.append(f"\n  --- 综合评分策略 ---\n")
            lines.append(_format_table(combo_slice))

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


# ────────────────────────── Excel 导出 ──────────────────────────

def export_backtest_excel(report: BacktestReport, output_path: str):
    """导出回测报告到 Excel。"""
    # Sheet1: 统计总览
    overview_rows = []
    all_results = report.signal_results + report.combo_results + report.random_results
    for r in all_results:
        overview_rows.append({
            "信号": r.signal_label, "卖出规则": r.exit_rule,
            "交易数": r.total_trades, "胜率%": round(r.win_rate, 1),
            "平均收益%": round(r.avg_return, 2),
            "最大收益%": round(r.max_return, 1),
            "最大亏损%": round(r.max_loss, 1),
            "盈亏比": round(r.profit_factor, 2),
            "累计收益%": round(r.cumulative_return, 1),
        })
    df_overview = pd.DataFrame(overview_rows)

    # Sheet2: 交易明细
    trade_rows = []
    for r in all_results:
        for t in r.trades:
            trade_rows.append({
                "信号": r.signal_label, "卖出规则": r.exit_rule,
                "代码": t.symbol, "买入日期": t.buy_date,
                "买入价": round(t.buy_price, 2),
                "卖出日期": t.sell_date, "卖出价": round(t.sell_price, 2),
                "持仓天数": t.hold_days, "收益率%": round(t.return_pct, 2),
                "退出原因": t.exit_reason,
            })
    df_trades = pd.DataFrame(trade_rows) if trade_rows else pd.DataFrame()

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_overview.to_excel(writer, sheet_name="统计总览", index=False)
        if not df_trades.empty:
            df_trades.to_excel(writer, sheet_name="交易明细", index=False)


# ────────────────────────── 对比图表 ──────────────────────────

def plot_backtest_comparison(report: BacktestReport, output_path: str):
    """生成回测对比柱状图。"""
    n_signals = len(SIGNAL_CONFIG)
    signal_labels = [cfg["label"] for cfg in SIGNAL_CONFIG]

    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    ax_wr, ax_ret = axes

    bar_width = 0.18
    x = np.arange(n_signals)
    rule_labels = [r["label"] for r in EXIT_RULES]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

    for rule_idx, exit_rule in enumerate(EXIT_RULES):
        sig_results = report.signal_results[rule_idx * n_signals:(rule_idx + 1) * n_signals]
        rand_result = report.random_results[rule_idx]

        win_rates = [r.win_rate for r in sig_results]
        avg_returns = [r.avg_return for r in sig_results]
        offset = (rule_idx - 1.5) * bar_width

        ax_wr.bar(x + offset, win_rates, bar_width, label=rule_labels[rule_idx],
                   color=colors[rule_idx], alpha=0.8)
        ax_ret.bar(x + offset, avg_returns, bar_width, label=rule_labels[rule_idx],
                    color=colors[rule_idx], alpha=0.8)

        # 随机基准线
        ax_wr.axhline(y=rand_result.win_rate, color=colors[rule_idx],
                       linestyle="--", alpha=0.4, linewidth=0.8)
        ax_ret.axhline(y=rand_result.avg_return, color=colors[rule_idx],
                        linestyle="--", alpha=0.4, linewidth=0.8)

    ax_wr.set_ylabel("胜率 (%)")
    ax_wr.set_title(f"{report.pool_name} 回测: 各信号胜率对比 (虚线=随机基准)")
    ax_wr.set_xticks(x)
    ax_wr.set_xticklabels(signal_labels, rotation=30, ha="right")
    ax_wr.legend(fontsize=9)
    ax_wr.grid(axis="y", alpha=0.3)
    ax_wr.axhline(y=50, color="gray", linewidth=0.5)

    ax_ret.set_ylabel("平均收益率 (%)")
    ax_ret.set_title(f"{report.pool_name} 回测: 各信号平均收益对比 (虚线=随机基准)")
    ax_ret.set_xticks(x)
    ax_ret.set_xticklabels(signal_labels, rotation=30, ha="right")
    ax_ret.legend(fontsize=9)
    ax_ret.grid(axis="y", alpha=0.3)
    ax_ret.axhline(y=0, color="gray", linewidth=0.5)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
