import unicodedata
from typing import List

import pandas as pd

from stock_cli.screener import ScreenResult, SIGNAL_CONFIG


def _display_width(s: str) -> int:
    """计算字符串的显示宽度（CJK 字符占 2 列）。"""
    width = 0
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ("W", "F") else 1
    return width


def _pad(s: str, width: int) -> str:
    """将字符串填充到指定显示宽度（右侧补空格）。"""
    return s + " " * (width - _display_width(s))


def format_terminal_table(results: List[ScreenResult]) -> str:
    """将筛选结果格式化为终端排名表格。"""
    valid = [r for r in results if r.error is None]
    failed = [r for r in results if r.error is not None]

    lines = []
    lines.append("=" * 72)
    lines.append(f"  {'排名':<6} {'代码':<14} {'得分':<10} {'触发信号'}")
    lines.append("-" * 72)

    for rank, r in enumerate(valid, 1):
        triggered = [s.label for s in r.signals if s.triggered]
        sig_str = ", ".join(triggered) if triggered else "-"
        score_str = f"{r.total_score}/{r.max_possible}"
        lines.append(f"  {str(rank):<6} {r.symbol:<14} {score_str:<10} {sig_str}")

    lines.append("=" * 72)

    if failed:
        lines.append("")
        lines.append("获取失败:")
        for r in failed:
            lines.append(f"  {r.symbol}: {r.error}")

    return "\n".join(lines)


def export_screen_excel(results: List[ScreenResult], output_path: str):
    """导出筛选结果到 Excel (两个 Sheet)。"""
    valid = [r for r in results if r.error is None]

    # Sheet 1: 筛选排名
    ranking_rows = []
    for rank, r in enumerate(valid, 1):
        row = {"排名": rank, "代码": r.symbol, "总分": r.total_score}
        for s in r.signals:
            row[s.label] = s.score
        ranking_rows.append(row)
    df_ranking = pd.DataFrame(ranking_rows)

    # Sheet 2: 信号详情
    detail_rows = []
    for r in valid:
        for s in r.signals:
            detail_rows.append({
                "代码": r.symbol,
                "信号": s.label,
                "是否触发": "是" if s.triggered else "否",
                "得分": s.score,
                "满分": s.max_score,
                "详情": s.detail,
            })
    df_detail = pd.DataFrame(detail_rows)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        if not df_ranking.empty:
            df_ranking.to_excel(writer, sheet_name="筛选排名", index=False)
        if not df_detail.empty:
            df_detail.to_excel(writer, sheet_name="信号详情", index=False)
