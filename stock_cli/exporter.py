import pandas as pd


def export_excel(df: pd.DataFrame, output_path: str):
    """导出股票数据到 Excel 文件。

    Args:
        df: 股票数据 DataFrame
        output_path: 输出文件路径
    """
    df_out = df.copy()
    df_out.index = df_out.index.strftime("%Y-%m-%d")
    df_out.to_excel(output_path, engine="openpyxl")
