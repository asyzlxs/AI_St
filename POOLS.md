# 股票池使用说明

## 新增的股票池

### 1. 互联互通（北向资金）

- **hgt** - 沪股通：通过港股通可以买入的上海股票
- **sgt** - 深股通：通过港股通可以买入的深圳股票

使用示例：
```bash
# 发现沪股通中的潜力股
stock discover --pool hgt --start 2025-07-01 --end 2026-04-13 --top 15

# 发现深股通中的潜力股
stock discover --pool sgt --start 2025-07-01 --end 2026-04-13 --top 15

# 回测沪股通策略
stock backtest --pool hgt --start 2024-04-08 --end 2026-04-08
```

### 2. 热门概念板块

- **newenergy** - 新能源：包含光伏、风电、储能等新能源相关股票
- **chip** - 芯片：包含半导体设计、制造、封测等芯片产业链股票
- **tech** - 科技创新：包含科技创新相关的股票
- **ai** - 人工智能：包含AI算法、算力、应用等人工智能产业链股票
- **ev** - 新能源车：包含整车、电池、零部件等新能源汽车产业链股票

使用示例：
```bash
# 发现芯片板块的潜力股
stock discover --pool chip --start 2025-07-01 --end 2026-04-13 --top 20

# 发现新能源板块的潜力股
stock discover --pool newenergy --start 2025-07-01 --end 2026-04-13 --min-score 30

# 发现人工智能板块的潜力股
stock discover --pool ai --start 2025-07-01 --end 2026-04-13 --top 15

# 回测新能源车板块策略
stock backtest --pool ev --start 2024-04-08 --end 2026-04-08
```

### 3. 原有的指数池

- **sz50** - 上证50
- **hs300** - 沪深300
- **zz500** - 中证500
- **cyb** - 创业板指

## 自定义概念和行业板块

除了预置的股票池，你还可以使用 `--concept` 和 `--industry` 参数来筛选任意概念或行业板块：

```bash
# 列出所有可用的概念板块
stock discover --list-concepts

# 列出所有可用的行业板块
stock discover --list-industries

# 使用自定义概念板块（例如：ChatGPT、量子科技等）
stock discover --concept ChatGPT --start 2025-07-01 --end 2026-04-13

# 使用自定义行业板块（例如：银行、医药等）
stock discover --industry 银行 --start 2025-07-01 --end 2026-04-13
```

## 组合使用

你可以组合使用多个板块进行筛选：

```bash
# 同时筛选新能源概念和行业
stock discover --pool newenergy --industry 新能源 --start 2025-07-01 --end 2026-04-13
```

## 注意事项

1. **网络依赖**：股票池数据通过 akshare 从网络实时获取，首次运行可能需要较长时间
2. **静态备份**：部分股票池提供了静态备份文件（位于 `stock_cli/data/` 目录），当网络获取失败时会自动使用
3. **数据更新**：建议定期运行以获取最新的成分股列表
4. **并发限制**：大批量筛选时请注意API调用频率限制

## 技术实现

- 指数成分股：使用 `akshare.index_stock_cons()`
- 沪深股通：使用 `akshare.stock_hk_ggt_components_em()`
- 概念板块：使用 `akshare.stock_board_concept_cons_em()`
- 行业板块：使用 `akshare.stock_board_industry_cons_em()`
