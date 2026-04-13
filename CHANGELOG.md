# 更新日志

## 2026-04-13 - 新增多板块支持

### 🎉 新增功能

#### 1. 新增股票池（13个）

**互联互通（北向资金）**
- `hgt` - 沪股通：港股通可买入的上海股票（1300+ 只）
- `sgt` - 深股通：港股通可买入的深圳股票

**热门概念板块**
- `newenergy` - 新能源：光伏、风电、储能等
- `chip` - 芯片：半导体设计、制造、封测
- `tech` - 科技创新：科技创新相关
- `ai` - 人工智能：AI算法、算力、应用
- `ev` - 新能源车：整车、电池、零部件

原有指数池保持不变：
- `sz50` - 上证50
- `hs300` - 沪深300
- `zz500` - 中证500
- `cyb` - 创业板指

#### 2. 新增自动化脚本

**⭐ daily_pool_analysis.sh** - 通用股票池分析脚本
- 支持命令行参数，可灵活切换 13 个股票池
- 默认分析沪股通（北向资金）
- 同时支持自选股分析
- 一键生成完整报告（Excel + 图表）

**multi_pool_analysis.sh** - 多板块并行分析
- 一次性分析多个板块
- 适合周末全面扫描
- 可自定义板块列表

#### 3. 完善文档

- **README.md** - 更新主文档，添加新池说明和快速开始
- **POOLS.md** - 新增股票池详细使用指南
- **SCRIPTS.md** - 新增自动化脚本使用指南
- **CHANGELOG.md** - 本更新日志

### 🔧 技术改进

#### pool_provider.py
- 扩展 `BUILTIN_POOLS` 支持多种类型（index/hk_connect/concept/industry）
- 新增 `get_pool_hk_connect()` - 获取沪深股通成分股
- 新增 `get_pool()` - 统一股票池获取接口
- 使用 `ak.stock_hsgt_hold_stock_em()` 获取北向资金持股

#### main.py
- 更新 `discover` 命令支持 13 个股票池
- 更新 `backtest` 命令支持 13 个股票池
- 更新帮助文档和使用示例

### 🎯 使用示例

```bash
# 分析沪股通潜力股（新功能）
stock discover --pool hgt --start 2025-07-01 --end 2026-04-13

# 分析芯片板块（新功能）
stock discover --pool chip --start 2025-07-01 --end 2026-04-13

# 使用自动化脚本（新功能）
./daily_pool_analysis.sh chip

# 多板块分析（新功能）
./multi_pool_analysis.sh

# 回测新能源车板块（新功能）
stock backtest --pool ev --start 2024-04-08 --end 2026-04-08
```

### 📊 数据来源

- 指数成分股：`akshare.index_stock_cons()`
- 沪深股通：`akshare.stock_hsgt_hold_stock_em()`
- 概念板块：`akshare.stock_board_concept_cons_em()`
- 行业板块：`akshare.stock_board_industry_cons_em()`

### ⚠️ 注意事项

1. 沪深股通数据量大（1300+ 只），完整分析需要较长时间
2. 建议使用 `--no-chart` 跳过图表生成以加快速度
3. 网络获取失败时会自动使用静态 fallback（需手动创建）
4. 部分股票可能退市，程序会自动跳过并继续

### 🔄 向后兼容

所有原有功能保持不变：
- 原有的 4 个指数池（sz50/hs300/zz500/cyb）正常工作
- 原有脚本（daily_analysis.sh 等）继续可用
- 所有命令行参数和行为保持一致

### 📝 文件清单

**新增文件**:
- `daily_pool_analysis.sh` - 通用股票池分析脚本 ⭐
- `multi_pool_analysis.sh` - 多板块并行分析
- `POOLS.md` - 股票池使用指南
- `SCRIPTS.md` - 脚本使用指南
- `CHANGELOG.md` - 更新日志

**修改文件**:
- `stock_cli/pool_provider.py` - 扩展股票池支持
- `stock_cli/main.py` - 更新命令选项
- `README.md` - 更新文档

**保留文件**:
- `daily_analysis.sh` - 创业板分析（向后兼容）
- `daily_analysis_hgt.sh` - 沪股通分析（已修复 API 调用）
- `daily_analysis_watchlist.sh` - 自选股分析

---

## 之前版本

### 2025-04-08 - 回测验证功能
- 新增 `stock backtest` 命令
- 对比技术指标策略 vs 随机买入
- 测试多种卖出规则

### 2025-04-08 - 自动发现功能
- 新增 `stock discover` 命令
- 支持指数成分股和行业/概念板块
- 自动筛选潜力股

### 2025-03-31 - 初始版本
- `stock query` - 单股数据查询
- `stock screen` - 技术面筛选
- 8 项技术指标评分系统
