import os
import json
import akshare as ak

def main():
    print("开始拉取 A 股代码-名称映射表...")
    try:
        # 获取沪深京所有股票的代码和名称
        df = ak.stock_info_a_code_name()
        cache = dict(zip(df['code'], df['name']))
        
        # 保存到 stock_cli/data/a_stock_names.json
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_cli", "data")
        os.makedirs(data_dir, exist_ok=True)
        
        out_file = os.path.join(data_dir, "a_stock_names.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 成功更新股票名称映射，共 {len(cache)} 条数据。")
        print(f"📁 文件已保存至: {out_file}")
    except Exception as e:
        print(f"❌ 获取失败，请检查网络或是否已关闭外网 VPN: {e}")

if __name__ == "__main__":
    main()
