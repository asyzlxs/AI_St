import os
import click
from stock_cli.fetcher import fetch_stock_data
from stock_cli.plotter import plot_stock, plot_screen_chart
from stock_cli.exporter import export_excel


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


def make_filename(symbol: str, start: str, end: str, ext: str) -> str:
    safe_symbol = symbol.replace(".", "_")
    return f"{safe_symbol}_{start}_{end}{ext}"


@click.group()
def cli():
    """股票数据查询工具 - 支持中国(A股)、美国、日本股票"""
    pass


@cli.command()
@click.argument("symbol")
@click.option("--start", required=True, help="开始日期 (YYYY-MM-DD)")
@click.option("--end", required=True, help="结束日期 (YYYY-MM-DD)")
def query(symbol: str, start: str, end: str):
    """查询股票数据，生成图表和Excel文件。

    SYMBOL: 股票代码，如 AAPL (美股), 600519.SS (上证), 0001.SZ (深证), 7203.T (日股)
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    click.echo(f"正在获取 {symbol} ({start} ~ {end}) 的数据...")
    try:
        df = fetch_stock_data(symbol, start, end)
    except ValueError as e:
        click.echo(f"错误: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"获取数据失败: {e}", err=True)
        raise SystemExit(1)

    click.echo(f"获取到 {len(df)} 条记录")

    png_path = os.path.join(OUTPUT_DIR, make_filename(symbol, start, end, ".png"))
    plot_stock(df, symbol, start, end, png_path)
    click.echo(f"图表已保存: {png_path}")

    xlsx_path = os.path.join(OUTPUT_DIR, make_filename(symbol, start, end, ".xlsx"))
    export_excel(df, xlsx_path)
    click.echo(f"Excel已保存: {xlsx_path}")


@cli.command()
@click.argument("symbols", nargs=-1)
@click.option("--file", "watchlist_file", type=click.Path(exists=True),
              default=None, help="包含股票代码的文件 (每行一个代码)")
@click.option("--start", required=True, help="开始日期 (YYYY-MM-DD)")
@click.option("--end", required=True, help="结束日期 (YYYY-MM-DD)")
@click.option("--min-score", default=0, type=int,
              help="最低分数阈值，仅显示达到此分数的股票 (默认: 0)")
@click.option("--no-chart", is_flag=True, default=False,
              help="不生成技术分析图表")
def screen(symbols, watchlist_file, start, end, min_score, no_chart):
    """技术筛选 - 对一组股票进行技术指标评分和排名。

    SYMBOLS: 一个或多个股票代码，如 AAPL TSLA 600519.SS

    \b
    支持从文件读取代码列表: --file watchlist.txt
    可组合使用: stock screen AAPL --file watchlist.txt --start 2025-01-01 --end 2026-04-01
    """
    from stock_cli.screener import screen_stocks, load_symbols_from_file
    from stock_cli.screen_formatter import format_terminal_table, export_screen_excel

    all_symbols = list(symbols)
    if watchlist_file:
        all_symbols.extend(load_symbols_from_file(watchlist_file))

    if not all_symbols:
        click.echo("错误: 请提供至少一个股票代码 (命令行参数或 --file)", err=True)
        raise SystemExit(1)

    # 去重保序
    seen = set()
    unique_symbols = []
    for s in all_symbols:
        s_upper = s.upper()
        if s_upper not in seen:
            seen.add(s_upper)
            unique_symbols.append(s)

    click.echo(f"正在筛选 {len(unique_symbols)} 只股票 ({start} ~ {end}) ...")

    def on_progress(idx, total, symbol):
        click.echo(f"  [{idx}/{total}] 分析 {symbol} ...")

    results = screen_stocks(unique_symbols, start, end, on_progress=on_progress)

    passed = [r for r in results if r.error is None and r.total_score >= min_score]
    failed = [r for r in results if r.error is not None]

    # 终端表格
    click.echo()
    click.echo(format_terminal_table(results))
    click.echo(f"\n共 {len(passed)} 只股票达到 {min_score} 分，{len(failed)} 只获取失败")

    # 导出 Excel
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    xlsx_path = os.path.join(OUTPUT_DIR, f"screen_{start}_{end}.xlsx")
    export_screen_excel(results, xlsx_path)
    click.echo(f"筛选结果已保存: {xlsx_path}")

    # 生成图表
    if not no_chart and passed:
        click.echo(f"正在生成 {len(passed)} 张技术分析图表 ...")
        for r in passed:
            chart_path = os.path.join(
                OUTPUT_DIR, make_filename(r.symbol, start, end, "_screen.png"))
            plot_screen_chart(
                r.df, r.indicators, r.symbol, r.signals,
                r.total_score, r.max_possible, chart_path,
            )
            click.echo(f"  图表已保存: {chart_path}")


@cli.command()
@click.option("--pool", type=click.Choice([
    "sz50", "hs300", "zz500", "cyb",           # 指数池
    "hgt", "sgt",                               # 沪深股通
    "newenergy", "chip", "tech", "ai", "ev"    # 热门概念
]), default=None, help="预置股票池")
@click.option("--concept", default=None, help="概念板块名称 (如: 半导体, ChatGPT)")
@click.option("--industry", default=None, help="行业板块名称 (如: 银行, 新能源)")
@click.option("--list-concepts", is_flag=True, default=False,
              help="列出所有可用的概念板块名称")
@click.option("--list-industries", is_flag=True, default=False,
              help="列出所有可用的行业板块名称")
@click.option("--start", default=None, help="开始日期 (YYYY-MM-DD)")
@click.option("--end", default=None, help="结束日期 (YYYY-MM-DD)")
@click.option("--min-score", default=20, type=int,
              help="最低分数阈值 (默认: 20)")
@click.option("--top", default=10, type=int,
              help="只显示前 N 名 (默认: 10)")
@click.option("--no-chart", is_flag=True, default=False,
              help="不生成技术分析图表")
def discover(pool, concept, industry, list_concepts, list_industries,
             start, end, min_score, top, no_chart):
    """自动发现潜力股 - 从指数成分/行业/概念板块中筛选。

    \b
    预置股票池:
      【指数池】
      sz50   - 上证50       hs300  - 沪深300
      zz500  - 中证500      cyb    - 创业板指

      【互联互通】
      hgt    - 沪股通       sgt    - 深股通

      【热门概念】
      newenergy - 新能源    chip   - 芯片
      tech      - 科技创新  ai     - 人工智能
      ev        - 新能源车

    \b
    示例:
      stock discover --pool hgt --start 2025-07-01 --end 2026-04-08
      stock discover --pool chip --start 2025-07-01 --end 2026-04-08 --top 15
      stock discover --concept 半导体 --start 2025-07-01 --end 2026-04-08
      stock discover --industry 新能源 --start 2025-07-01 --end 2026-04-08 --top 5
      stock discover --list-concepts
    """
    from stock_cli.pool_provider import (
        BUILTIN_POOLS, get_pool, get_pool_by_concept,
        get_pool_by_industry, list_concepts as _list_concepts,
        list_industries as _list_industries,
    )
    from stock_cli.screener import screen_stocks
    from stock_cli.screen_formatter import format_terminal_table, export_screen_excel

    # 列出板块名称模式
    if list_concepts:
        names = _list_concepts()
        if names:
            click.echo(f"可用概念板块 ({len(names)} 个):\n")
            for i, name in enumerate(names, 1):
                click.echo(f"  {name}", nl=False)
                click.echo("" if i % 5 == 0 else "\t", nl=(i % 5 == 0))
            click.echo()
        else:
            click.echo("获取概念板块列表失败，请检查网络连接")
        return

    if list_industries:
        names = _list_industries()
        if names:
            click.echo(f"可用行业板块 ({len(names)} 个):\n")
            for i, name in enumerate(names, 1):
                click.echo(f"  {name}", nl=False)
                click.echo("" if i % 5 == 0 else "\t", nl=(i % 5 == 0))
            click.echo()
        else:
            click.echo("获取行业板块列表失败，请检查网络连接")
        return

    # 必须指定至少一个数据源
    if not pool and not concept and not industry:
        click.echo("错误: 请指定 --pool, --concept 或 --industry", err=True)
        click.echo("可用池: " + ", ".join(
            f"{k} ({v['name']})" for k, v in BUILTIN_POOLS.items()))
        raise SystemExit(1)

    if not start or not end:
        click.echo("错误: 请指定 --start 和 --end 日期", err=True)
        raise SystemExit(1)

    # 获取股票池
    symbols = []
    source_name = ""

    if pool:
        pool_info = BUILTIN_POOLS[pool]
        source_name = pool_info["name"]
        click.echo(f"正在获取 {source_name} 成分股 ...")
        symbols = get_pool(pool)

    if concept:
        source_name = f"概念: {concept}"
        click.echo(f"正在获取概念板块 '{concept}' 成分股 ...")
        symbols.extend(get_pool_by_concept(concept))

    if industry:
        source_name = f"行业: {industry}"
        click.echo(f"正在获取行业板块 '{industry}' 成分股 ...")
        symbols.extend(get_pool_by_industry(industry))

    if not symbols:
        click.echo("错误: 未获取到任何股票代码", err=True)
        raise SystemExit(1)

    # 去重
    seen = set()
    unique = []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    symbols = unique

    click.echo(f"共 {len(symbols)} 只候选股票，开始筛选 ({start} ~ {end}) ...")

    def on_progress(idx, total, symbol):
        click.echo(f"  [{idx}/{total}] 分析 {symbol} ...")

    results = screen_stocks(symbols, start, end, on_progress=on_progress)

    # 过滤有效结果
    valid = [r for r in results if r.error is None and r.total_score >= min_score]
    failed = [r for r in results if r.error is not None]

    # 取 top N
    display_results = valid[:top]

    # 终端表格
    click.echo()
    click.echo(f"=== {source_name}  得分 >= {min_score}  Top {top} ===\n")
    click.echo(format_terminal_table(display_results))
    click.echo(f"\n{len(valid)} 只达到 {min_score} 分 (共 {len(symbols)} 只，"
               f"{len(failed)} 只获取失败)")

    # 导出 Excel (全量结果)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_source = (pool or concept or industry or "discover").replace(" ", "_")
    xlsx_path = os.path.join(OUTPUT_DIR, f"discover_{safe_source}_{start}_{end}.xlsx")
    export_screen_excel(results, xlsx_path)
    click.echo(f"筛选结果已保存: {xlsx_path}")

    # 为 top 结果生成图表
    if not no_chart and display_results:
        click.echo(f"正在生成 {len(display_results)} 张技术分析图表 ...")
        for r in display_results:
            chart_path = os.path.join(
                OUTPUT_DIR, make_filename(r.symbol, start, end, "_discover.png"))
            plot_screen_chart(
                r.df, r.indicators, r.symbol, r.signals,
                r.total_score, r.max_possible, chart_path,
            )
            click.echo(f"  图表已保存: {chart_path}")


@cli.command()
@click.argument("symbols", nargs=-1)
@click.option("--pool", type=click.Choice([
    "sz50", "hs300", "zz500", "cyb",           # 指数池
    "hgt", "sgt",                               # 沪深股通
    "newenergy", "chip", "tech", "ai", "ev"    # 热门概念
]), default=None, help="预置股票池")
@click.option("--start", required=True, help="开始日期 (YYYY-MM-DD)")
@click.option("--end", required=True, help="结束日期 (YYYY-MM-DD)")
@click.option("--random-n", default=1000, type=int,
              help="随机策略模拟次数 (默认: 1000)")
@click.option("--no-chart", is_flag=True, default=False,
              help="不生成对比图表")
def backtest(symbols, pool, start, end, random_n, no_chart):
    """回测验证 - 检验技术指标的实际选股效果。

    \b
    对比信号策略 vs 随机买入的胜率和收益率。
    测试4种卖出规则: 持仓5天/10天/20天 + 止盈10%止损5%。

    \b
    示例:
      stock backtest --pool cyb --start 2024-04-08 --end 2026-04-08
      stock backtest --pool chip --start 2024-04-08 --end 2026-04-08
      stock backtest 300677.SZ 300750.SZ --start 2025-01-01 --end 2026-04-08
    """
    from stock_cli.backtester import (
        run_backtest, format_backtest_report,
        export_backtest_excel, plot_backtest_comparison,
    )
    from stock_cli.pool_provider import BUILTIN_POOLS, get_pool

    all_symbols = list(symbols)
    pool_name = "自选股票"

    if pool:
        pool_info = BUILTIN_POOLS[pool]
        pool_name = pool_info["name"]
        click.echo(f"正在获取 {pool_name} 成分股 ...")
        all_symbols.extend(get_pool(pool))

    if not all_symbols:
        click.echo("错误: 请提供股票代码或 --pool", err=True)
        raise SystemExit(1)

    # 去重
    seen = set()
    unique = []
    for s in all_symbols:
        if s not in seen:
            seen.add(s)
            unique.append(s)

    click.echo(f"开始回测: {pool_name} {len(unique)} 只股票 ({start} ~ {end})")
    click.echo(f"随机基准模拟次数: {random_n}\n")

    def on_progress(idx, total, symbol, phase):
        click.echo(f"  [{phase}] [{idx}/{total}] {symbol}")

    report = run_backtest(unique, start, end, pool_name=pool_name,
                           random_n=random_n, on_progress=on_progress)

    # 打印报告
    click.echo()
    click.echo(format_backtest_report(report))

    # 导出 Excel
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_pool = (pool or "custom").replace(" ", "_")
    xlsx_path = os.path.join(OUTPUT_DIR, f"backtest_{safe_pool}_{start}_{end}.xlsx")
    export_backtest_excel(report, xlsx_path)
    click.echo(f"\nExcel 报告已保存: {xlsx_path}")

    # 对比图表
    if not no_chart:
        chart_path = os.path.join(OUTPUT_DIR, f"backtest_{safe_pool}_{start}_{end}.png")
        plot_backtest_comparison(report, chart_path)
        click.echo(f"对比图表已保存: {chart_path}")


if __name__ == "__main__":
    cli()
