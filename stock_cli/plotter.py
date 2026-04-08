import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import pandas as pd

# 配置 CJK 字体（macOS 优先 Heiti TC，回退 Arial Unicode MS）
_CJK_FONTS = ["Heiti TC", "Hiragino Sans GB", "Arial Unicode MS", "SimHei"]
_CJK_FONT = None
for _name in _CJK_FONTS:
    if any(f.name == _name for f in fm.fontManager.ttflist):
        _CJK_FONT = _name
        break
if _CJK_FONT:
    plt.rcParams["font.sans-serif"] = [_CJK_FONT] + plt.rcParams["font.sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False


def plot_stock(df: pd.DataFrame, symbol: str, start: str, end: str, output_path: str):
    """绘制收盘价折线图并保存为 PNG。

    Args:
        df: 股票数据 DataFrame
        symbol: 股票代码
        start: 开始日期
        end: 结束日期
        output_path: 输出文件路径
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(df.index, df["Close"], color="#1f77b4", linewidth=1.5)
    ax.set_title(f"{symbol}  ({start} ~ {end})", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Close Price", fontsize=11)
    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=45)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_screen_chart(df: pd.DataFrame, indicators: dict, symbol: str,
                       signals: list, total_score: int, max_score: int,
                       output_path: str):
    """绘制带技术指标的三子图分析图表（价格+均线 / 成交量 / MACD）。

    Args:
        df: OHLCV DataFrame
        indicators: dict 包含 MA5, MA20, MA60, MACD, Signal, Histogram
        symbol: 股票代码
        signals: List[SignalResult]，仅显示已触发的信号
        total_score: 总分
        max_score: 满分
        output_path: 输出文件路径
    """
    fig, axes = plt.subplots(
        3, 1, figsize=(14, 10), sharex=True,
        gridspec_kw={"height_ratios": [3, 1, 1]},
    )
    ax_price, ax_vol, ax_macd = axes

    # ========== Subplot 1: Price + MAs ==========
    ax_price.plot(df.index, df["Close"], color="black", linewidth=1.5, label="Close")
    if "MA5" in indicators:
        ax_price.plot(df.index, indicators["MA5"], color="#1f77b4",
                       linewidth=1.0, label="MA5", alpha=0.8)
    if "MA20" in indicators:
        ax_price.plot(df.index, indicators["MA20"], color="#ff7f0e",
                       linewidth=1.0, label="MA20", alpha=0.8)
    if "MA60" in indicators:
        ax_price.plot(df.index, indicators["MA60"], color="#d62728",
                       linewidth=1.0, label="MA60", linestyle="--", alpha=0.8)

    ax_price.set_title(
        f"{symbol}  Score: {total_score}/{max_score}",
        fontsize=14, fontweight="bold",
    )
    ax_price.set_ylabel("Price", fontsize=11)
    ax_price.grid(True, alpha=0.3)
    ax_price.legend(loc="upper left", fontsize=9)

    # 右上角文本框列出已触发信号
    triggered = [s for s in signals if s.triggered]
    if triggered:
        text = "Triggered Signals:\n" + "\n".join(
            f"  + {s.label} ({s.score})" for s in triggered
        )
        ax_price.text(
            0.99, 0.97, text, transform=ax_price.transAxes,
            fontsize=9, verticalalignment="top", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow",
                      edgecolor="gray", alpha=0.85),
        )

    # ========== Subplot 2: Volume ==========
    colors = ["#26a69a" if c >= o else "#ef5350"
              for c, o in zip(df["Close"], df["Open"])]
    ax_vol.bar(df.index, df["Volume"], color=colors, width=0.8, alpha=0.8)
    avg_vol = df["Volume"].rolling(window=20).mean()
    ax_vol.plot(df.index, avg_vol, color="#ff7f0e", linewidth=1.0, label="Vol MA20")
    ax_vol.set_ylabel("Volume", fontsize=11)
    ax_vol.grid(True, alpha=0.3)
    ax_vol.legend(loc="upper left", fontsize=9)

    # ========== Subplot 3: MACD ==========
    if "MACD" in indicators and "Signal" in indicators and "Histogram" in indicators:
        ax_macd.plot(df.index, indicators["MACD"], color="#1f77b4",
                      linewidth=1.0, label="MACD")
        ax_macd.plot(df.index, indicators["Signal"], color="#ff7f0e",
                      linewidth=1.0, label="Signal")
        hist = indicators["Histogram"]
        hist_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in hist.fillna(0)]
        ax_macd.bar(df.index, hist, color=hist_colors, width=0.8, alpha=0.7)
        ax_macd.axhline(y=0, color="gray", linewidth=0.5)
    ax_macd.set_ylabel("MACD", fontsize=11)
    ax_macd.set_xlabel("Date", fontsize=11)
    ax_macd.grid(True, alpha=0.3)
    ax_macd.legend(loc="upper left", fontsize=9)

    ax_macd.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=45)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
