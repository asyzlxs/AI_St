import os
from typing import List, Optional

import click


BUILTIN_POOLS = {
    "sz50":  {"name": "上证50",   "index_code": "000016"},
    "hs300": {"name": "沪深300",  "index_code": "000300"},
    "zz500": {"name": "中证500",  "index_code": "000905"},
    "cyb":   {"name": "创业板指",  "index_code": "399006"},
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
