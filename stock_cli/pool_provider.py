import os
from typing import List, Optional

import click


BUILTIN_POOLS = {
    # 指数池
    "sz50":  {"name": "上证50",   "index_code": "000016"},
    "hs300": {"name": "沪深300",  "index_code": "000300"},
    "zz500": {"name": "中证500",  "index_code": "000905"},
    "cyb":   {"name": "创业板指",  "index_code": "399006"},

    # 全市场
    "hgt":   {"name": "沪市A股",  "type": "exchange_all", "exchange": "sh"},
    "sgt":   {"name": "深市A股",  "type": "exchange_all", "exchange": "sz"},

    # 热门概念板块
    "newenergy": {"name": "新能源",     "type": "concept", "concept_name": "新能源"},
    "chip":      {"name": "芯片",       "type": "concept", "concept_name": "芯片"},
    "tech":      {"name": "科技创新",   "type": "concept", "concept_name": "科技创新"},
    "ai":        {"name": "人工智能",   "type": "concept", "concept_name": "人工智能"},
    "ev":        {"name": "新能源车",   "type": "concept", "concept_name": "新能源车"},
}

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _to_yfinance_symbol(code: str) -> str:
    """将 A 股纯数字代码转为 yfinance 格式 (600xxx.SS / 其他.SZ)。"""
    code = code.strip()
    if code.endswith((".SS", ".SZ", ".HK", ".T")):
        return code
    if code.startswith("6"):
        return f"{code}.SS"
    return f"{code}.SZ"


def _load_static_fallback(pool_key: str) -> Optional[List[str]]:
    """从 stock_cli/data/{pool_key}.txt 加载静态股票列表。"""
    filepath = os.path.join(_DATA_DIR, f"{pool_key}.txt")
    if not os.path.exists(filepath):
        return None
    symbols = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                symbols.append(line)
    return symbols if symbols else None


def get_pool_by_index(index_code: str, pool_key: str = "") -> List[str]:
    """通过 akshare 获取指数成分股，失败时使用静态 fallback。"""
    try:
        import akshare as ak
        df = ak.index_stock_cons(symbol=index_code)
        codes = df["品种代码"].tolist()
        symbols = [_to_yfinance_symbol(c) for c in codes]
        if symbols:
            return symbols
    except Exception as e:
        click.echo(f"  akshare 获取失败: {e}", err=True)

    # fallback
    if pool_key:
        static = _load_static_fallback(pool_key)
        if static:
            click.echo(f"  使用静态列表 fallback ({len(static)} 只)")
            return static

    return []


def get_pool_by_concept(name: str) -> List[str]:
    """通过 akshare 获取概念板块成分股。"""
    try:
        import akshare as ak
        df = ak.stock_board_concept_cons_em(symbol=name)
        codes = df["代码"].tolist()
        return [_to_yfinance_symbol(c) for c in codes]
    except Exception as e:
        click.echo(f"  获取概念板块 '{name}' 失败: {e}", err=True)
        return []


def get_pool_by_industry(name: str) -> List[str]:
    """通过 akshare 获取行业板块成分股。"""
    try:
        import akshare as ak
        df = ak.stock_board_industry_cons_em(symbol=name)
        codes = df["代码"].tolist()
        return [_to_yfinance_symbol(c) for c in codes]
    except Exception as e:
        click.echo(f"  获取行业板块 '{name}' 失败: {e}", err=True)
        return []


def list_concepts() -> List[str]:
    """列出所有可用的概念板块名称。"""
    try:
        import akshare as ak
        df = ak.stock_board_concept_name_em()
        return df["板块名称"].tolist()
    except Exception as e:
        click.echo(f"  获取概念板块列表失败: {e}", err=True)
        return []


def list_industries() -> List[str]:
    """列出所有可用的行业板块名称。"""
    try:
        import akshare as ak
        df = ak.stock_board_industry_name_em()
        return df["板块名称"].tolist()
    except Exception as e:
        click.echo(f"  获取行业板块列表失败: {e}", err=True)
        return []


def get_pool_exchange_all(exchange: str) -> List[str]:
    """获取沪市或深市全部 A 股。

    Args:
        exchange: "sh" 沪市（主板+科创板），"sz" 深市（A股列表）
    """
    try:
        import akshare as ak
        codes: List[str] = []
        if exchange == "sh":
            for sub in ("主板A股", "科创板"):
                df = ak.stock_info_sh_name_code(symbol=sub)
                codes.extend(str(c) for c in df["证券代码"].tolist())
        else:
            df = ak.stock_info_sz_name_code(symbol="A股列表")
            codes.extend(str(c) for c in df["A股代码"].tolist())

        symbols = [_to_yfinance_symbol(c) for c in codes]
        if symbols:
            name = "沪市A股" if exchange == "sh" else "深市A股"
            click.echo(f"  获取到 {len(symbols)} 只{name}")
            return symbols
    except Exception as e:
        click.echo(f"  获取{exchange}市A股列表失败: {e}", err=True)
        pool_key = "hgt" if exchange == "sh" else "sgt"
        static = _load_static_fallback(pool_key)
        if static:
            click.echo(f"  使用静态列表 fallback ({len(static)} 只)")
            return static
    return []


def get_pool(pool_key: str) -> List[str]:
    """根据 pool_key 统一获取股票池。"""
    if pool_key not in BUILTIN_POOLS:
        return []

    pool_info = BUILTIN_POOLS[pool_key]
    pool_type = pool_info.get("type", "index")

    if pool_type == "index":
        # 指数成分股
        return get_pool_by_index(pool_info["index_code"], pool_key=pool_key)
    elif pool_type == "exchange_all":
        # 沪市/深市全部 A 股
        return get_pool_exchange_all(pool_info["exchange"])
    elif pool_type == "concept":
        # 概念板块
        return get_pool_by_concept(pool_info["concept_name"])
    elif pool_type == "industry":
        # 行业板块
        return get_pool_by_industry(pool_info["industry_name"])

    return []
