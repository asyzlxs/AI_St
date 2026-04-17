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
    lines.append("=" * 120)
    lines.append(f"  {'名字':<24} {'排名':<6} {'代码':<14} {'当前价格':<12} {'得分':<10} {'触发信号'}")
    lines.append("-" * 120)

    for rank, r in enumerate(valid, 1):
        triggered = [s.label for s in r.signals if s.triggered]
        sig_str = ", ".join(triggered) if triggered else "-"
        score_str = f"{r.total_score}/{r.max_possible}"
        price_str = f"{r.current_price:.2f}" if r.current_price is not None else "N/A"
        # 处理中文名称显示：如果名称显示宽度超过24，截断并添加省略号
        name_str = r.name or '-'
        if _display_width(name_str) > 24:
            # 逐字符截断直到宽度合适
            truncated = ''
            for ch in name_str:
                if _display_width(truncated + ch + '..') <= 24:
                    truncated += ch
                else:
                    break
            name_str = truncated + '..'
        # 填充到24宽度
        name_str = _pad(name_str, 24)
        lines.append(f"  {name_str} {str(rank):<6} {r.symbol:<14} {price_str:<12} {score_str:<10} {sig_str}")

    lines.append("=" * 120)

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
    # 定义固定的列顺序
    base_columns = ["名字", "排名", "代码", "当前价格", "总分"]
    signal_labels = [s["label"] for s in SIGNAL_CONFIG]
    all_columns = base_columns + signal_labels

    for rank, r in enumerate(valid, 1):
        # 按照 all_columns 的顺序构建每一行，使用列表而不是字典
        row = []
        # 添加基础列
        row.append(r.name or '-')  # 名字
        row.append(rank)  # 排名
        row.append(r.symbol)  # 代码
        row.append(r.current_price)  # 当前价格
        row.append(r.total_score)  # 总分

        # 按照 SIGNAL_CONFIG 的顺序添加各个信号的��分
        signal_scores = {s.name: s.score for s in r.signals}
        for cfg in SIGNAL_CONFIG:
            row.append(signal_scores.get(cfg["name"], 0))

        ranking_rows.append(row)

    df_ranking = pd.DataFrame(ranking_rows, columns=all_columns)

    # Sheet 2: 信号详情
    detail_rows = []
    detail_columns = ["名字", "代码", "当前价格", "信号", "是否触发", "得分", "满分", "详情"]

    for r in valid:
        for s in r.signals:
            detail_rows.append({
                "名字": r.name or '-',
                "代码": r.symbol,
                "当前价格": r.current_price,
                "信号": s.label,
                "是否触发": "是" if s.triggered else "否",
                "得分": s.score,
                "满分": s.max_score,
                "详情": s.detail,
            })
    df_detail = pd.DataFrame(detail_rows, columns=detail_columns)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        if not df_ranking.empty:
            df_ranking.to_excel(writer, sheet_name="筛选排名", index=False)
        if not df_detail.empty:
            df_detail.to_excel(writer, sheet_name="信号详情", index=False)
