# Stock CLI - 股票数据分析工具

命令行股票分析工具，支持 A股、港股、美股、日股等市场。提供数据查询、技术面筛选、自动发现潜力股、回测验证四大功能。

> 🚀 **快速开始**: 查看 [QUICKSTART.md](QUICKSTART.md) | 📖 **脚本指南**: [SCRIPTS.md](SCRIPTS.md) | 📊 **股票池说明**: [POOLS.md](POOLS.md)

## 功能概览

| 命令 | 功能 | 说明 |
|------|------|------|
| `stock query` | 数据查询 | 获取单只股票数据，生成K线图和Excel |
| `stock screen` | 技术筛选 | 对指定股票进行8项技术指标评分排名 |
| `stock discover` | 自动发现 | 从指数/板块中自动获取股票池并筛选潜力股 |
| `stock backtest` | 回测验证 | 检验技术指标的实际选股效果，对比随机买入 |

## 快速开始

### 一键自动化分析（推荐）

```bash
# 1. 激活环境
conda activate stock_cli

# 2. 分析沪股通潜力股（默认）
./daily_pool_analysis.sh

# 3. 或分析其他板块
./daily_pool_analysis.sh chip         # 芯片板块
./daily_pool_analysis.sh newenergy    # 新能源板块
./daily_pool_analysis.sh cyb          # 创业板
```

### 手动命令使用

```bash
# 发现沪股通潜力股
stock discover --pool hgt --start 2025-07-01 --end 2026-04-13

# 筛选自选股
stock screen 600519.SS 300750.SZ --start 2025-07-01 --end 2026-04-13

# 查询单只股票
stock query AAPL --start 2025-01-01 --end 2026-04-13
```

## 环境搭建

### 1. 创建 conda 虚拟环境

```bash
# 创建 Python 3.11 的虚拟环境
conda create -n stock_cli python=3.11 -y

# 激活环境
conda activate stock_cli
```

### 2. 安装依赖包

```bash
# 方式一：通过 pip install -e . 一键安装（推荐）
pip install -e .

# 方式二：手动安装各依赖
pip install yfinance>=0.2.0      # Yahoo Finance 股票数据
pip install akshare>=1.10.0      # A股指数成分/行业板块数据
pip install pandas>=1.4.0        # 数据处理
pip install matplotlib>=3.5.0    # 图表绘制
pip install click>=8.0.0         # CLI 命令行框架
pip install openpyxl>=3.0.0      # Excel 导出
```

### 3. 验证安装

```bash
# 确保在 stock_cli 环境中
conda activate stock_cli

# 查看帮助
stock --help

# 快速测试：查询苹果近一个月数据
stock query AAPL --start 2026-03-01 --end 2026-04-09
```

### 依赖说明

| 包名 | 用途 | 说明 |
|------|------|------|
| yfinance | 股票数据获取 | 支持全球市场 (A股/港股/美股/日股) |
| akshare | A股板块数据 | 获取指数成分股、行业/概念板块 |
| pandas | 数据处理 | DataFrame 操作、时间序列处理 |
| matplotlib | 图表绘制 | K线图、技术分析三子图、回测对比图 |
| click | CLI 框架 | 命令行参数解析、子命令管理 |
| openpyxl | Excel 导出 | 生成 .xlsx 筛选报告和回测报告 |

## 股票代码格式

| 市场 | 格式 | 示例 |
|------|------|------|
| A股上证 | 代码.SS | 600519.SS (贵州茅台) |
| A股深证 | 代码.SZ | 300750.SZ (宁德时代) |
| 港股 | 代码.HK | 0700.HK (腾讯控股) |
| 美股 | 直接代码 | AAPL (苹果) |
| 日股 | 代码.T | 7203.T (丰田汽车) |

---

## 一、stock query - 数据查询

获取单只股票的历史数据，生成收盘价折线图和 Excel 文件。

### 基本用法

```bash
stock query <股票代码> --start <开始日期> --end <结束日期>
```

### 示例

```bash
# A股
stock query 600519.SS --start 2024-01-01 --end 2024-12-31   # 贵州茅台
stock query 300750.SZ --start 2024-01-01 --end 2024-12-31   # 宁德时代

# 港股
stock query 0700.HK --start 2024-01-01 --end 2024-12-31     # 腾讯控股

# 美股
stock query AAPL --start 2024-01-01 --end 2024-12-31        # 苹果
stock query NVDA --start 2024-01-01 --end 2024-12-31        # 英伟达

# 日股
stock query 7203.T --start 2024-01-01 --end 2024-12-31      # 丰田汽车
```

### 输出文件

```
output/
  AAPL_2024-01-01_2024-12-31.png       # 收盘价折线图
  AAPL_2024-01-01_2024-12-31.xlsx      # OHLCV 数据表
```

---

## 二、stock screen - 技术面筛选

对你指定的一组股票进行 8 项技术指标评分（满分 100），输出排名表格、Excel 和技术分析图表。

### 评分体系

| 信号 | 分值 | 含义 |
|------|------|------|
| 金叉 (MA5 x MA20) | 15 | 短期均线上穿中期均线，趋势启动 |
| 多头排列 | 10 | Close > MA5 > MA20 > MA60，上升趋势确认 |
| RSI 超卖反弹 | 15 | RSI 从 30 以下回升，均值回归信号 |
| MACD 柱转正 | 10 | MACD 柱状图从负转正，动量转多 |
| MACD 底背离 | 20 | 价格新低但 MACD 未新低，最强反转信号 |
| 放量突破 | 10 | 当日成交量超过 20 日均量 2 倍 |
| 60 日新高 | 10 | 收盘价创近 60 个交易日新高 |
| 波动率突破 | 10 | ATR 收缩后放大，蓄力突破 |

### 基本用法

```bash
stock screen <代码1> <代码2> ... --start <开始日期> --end <结束日期>
```

### 全部选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--start` | 开始日期 (YYYY-MM-DD) | 必填 |
| `--end` | 结束日期 (YYYY-MM-DD) | 必填 |
| `--file` | 从文件读取股票代码 (每行一个) | - |
| `--min-score` | 最低分数阈值 | 0 |
| `--no-chart` | 不生成技术分析图表 | 生成 |

### 示例

```bash
# 筛选几只美股
stock screen AAPL TSLA NVDA GOOGL MSFT --start 2025-07-01 --end 2026-04-08

# 筛选 A 股
stock screen 600519.SS 300750.SZ 000858.SZ --start 2025-07-01 --end 2026-04-08

# 混合市场
stock screen AAPL 0700.HK 600519.SS --start 2025-07-01 --end 2026-04-08

# 从文件读取代码列表
stock screen --file watchlist.txt --start 2025-07-01 --end 2026-04-08

# 命令行 + 文件组合，只看 30 分以上
stock screen 600418.SS --file my_stocks.txt --start 2025-07-01 --end 2026-04-08 --min-score 30

# 只要排名表格，不生成图表（更快）
stock screen AAPL TSLA NVDA --start 2025-07-01 --end 2026-04-08 --no-chart
```

### watchlist 文件格式

每行一个股票代码，`#` 开头为注释：

```text
# 我的自选股
AAPL
TSLA
600519.SS
300750.SZ
0700.HK
```

### 输出文件

```
output/
  screen_2025-07-01_2026-04-08.xlsx           # 筛选结果 (含排名表和信号详情两个Sheet)
  AAPL_2025-07-01_2026-04-08_screen.png       # 技术分析图表 (价格+均线/成交量/MACD)
  TSLA_2025-07-01_2026-04-08_screen.png
  ...
```

### 输出示例

```
========================================================================
  排名     代码             得分         触发信号
------------------------------------------------------------------------
  1      600418.SS      25/100     RSI超卖反弹, MACD柱转正
  2      603009.SS      10/100     MACD柱转正
  3      002130.SZ      0/100      -
========================================================================
```

---

## 三、stock discover - 自动发现潜力股

不需要手动提供股票代码。从预置的指数成分股或行业/概念板块中自动获取候选池，然后用技术指标筛选出潜力股。

### 预置股票池

**指数池**

| 参数 | 股票池 | 成分股数量 |
|------|--------|-----------|
| `--pool sz50` | 上证 50 | 50 只 |
| `--pool hs300` | 沪深 300 | 300 只 |
| `--pool zz500` | 中证 500 | 500 只 |
| `--pool cyb` | 创业板指 | 100 只 |

**互联互通（北向资金）**

| 参数 | 股票池 | 说明 |
|------|--------|------|
| `--pool hgt` | 沪股通 | 港股通可买入的上海股票 |
| `--pool sgt` | 深股通 | 港股通可买入的深圳股票 |

**热门概念板块**

| 参数 | 股票池 | 说明 |
|------|--------|------|
| `--pool newenergy` | 新能源 | 光伏、风电、储能等 |
| `--pool chip` | 芯片 | 半导体设计、制造、封测 |
| `--pool tech` | 科技创新 | 科技创新相关 |
| `--pool ai` | 人工智能 | AI算法、算力、应用 |
| `--pool ev` | 新能源车 | 整车、电池、零部件 |

### 全部选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--pool` | 预置股票池 (sz50/hs300/zz500/cyb/hgt/sgt/newenergy/chip/tech/ai/ev) | - |
| `--concept` | 概念板块名称 (如: 半导体) | - |
| `--industry` | 行业板块名称 (如: 新能源) | - |
| `--list-concepts` | 列出所有可用概念板块 | - |
| `--list-industries` | 列出所有可用行业板块 | - |
| `--start` | 开始日期 (YYYY-MM-DD) | 必填 |
| `--end` | 结束日期 (YYYY-MM-DD) | 必填 |
| `--min-score` | 最低分数阈值 | 20 |
| `--top` | 只显示前 N 名 | 10 |
| `--no-chart` | 不生成技术分析图表 | 生成 |

### 示例

```bash
# === 从预置指数池中发现 ===

# 上证 50 中找潜力股（最常用）
stock discover --pool sz50 --start 2025-07-01 --end 2026-04-08

# 创业板指 Top 10
stock discover --pool cyb --start 2025-07-01 --end 2026-04-08

# 沪深 300 中得分 >= 30 的 Top 5
stock discover --pool hs300 --start 2025-07-01 --end 2026-04-08 --min-score 30 --top 5

# 中证 500，不生成图表（大池子建议加 --no-chart 加速）
stock discover --pool zz500 --start 2025-07-01 --end 2026-04-08 --no-chart

# === 从北向资金中发现（沪深股通） ===

# 沪股通潜力股
stock discover --pool hgt --start 2025-07-01 --end 2026-04-08 --top 15

# 深股通潜力股
stock discover --pool sgt --start 2025-07-01 --end 2026-04-08 --top 15

# === 从热门概念板块中发现 ===

# 芯片板块
stock discover --pool chip --start 2025-07-01 --end 2026-04-08 --top 20

# 新能源板块，得分 >= 30
stock discover --pool newenergy --start 2025-07-01 --end 2026-04-08 --min-score 30

# 人工智能板块
stock discover --pool ai --start 2025-07-01 --end 2026-04-08

# 新能源车板块
stock discover --pool ev --start 2025-07-01 --end 2026-04-08 --top 15

# === 从行业/概念板块中发现（需要东方财富网络可达）===

# 半导体概念板块
stock discover --concept 半导体 --start 2025-07-01 --end 2026-04-08

# 新能源行业板块
stock discover --industry 新能源 --start 2025-07-01 --end 2026-04-08

# === 查看可用板块名称 ===

# 列出所有概念板块
stock discover --list-concepts

# 列出所有行业板块
stock discover --list-industries
```

### 输出示例

```
正在获取 创业板指 成分股 ...
共 100 只候选股票，开始筛选 (2025-07-01 ~ 2026-04-08) ...
  [1/100] 分析 300100.SZ ...
  [2/100] 分析 300255.SZ ...
  ...

=== 创业板指  得分 >= 20  Top 10 ===

========================================================================
  排名     代码             得分         触发信号
------------------------------------------------------------------------
  1      300677.SZ      40/100     多头排列, MACD柱转正, 60日新高, 波动率突破
  2      300255.SZ      30/100     金叉 (MA5×MA20), RSI超卖反弹
  3      300866.SZ      30/100     MACD底背离, 波动率突破
  ...
========================================================================

16 只达到 20 分 (共 100 只，0 只获取失败)
```

### 输出文件

```
output/
  discover_cyb_2025-07-01_2026-04-08.xlsx           # 全量筛选结果
  300677_SZ_2025-07-01_2026-04-08_discover.png      # Top 股票的技术分析图表
  300255_SZ_2025-07-01_2026-04-08_discover.png
  ...
```

---

## 四、自动化分析脚本

为了方便每日定时分析，项目提供了开箱即用的自动化脚本。

> 📖 **详细说明请查看**: [SCRIPTS.md](SCRIPTS.md)

### daily_pool_analysis.sh - 股票池每日分析 ⭐推荐

自动分析指定股票池的潜力股 + 自选股，一键生成完整报告。

#### 基本用法

```bash
./daily_pool_analysis.sh [POOL]
```

#### 支持的股票池

| 类别 | 股票池代码 | 说明 |
|------|-----------|------|
| **指数池** | sz50, hs300, zz500, cyb | 上证50/沪深300/中证500/创业板指 |
| **互联互通** | hgt, sgt | 沪股通/深股通（北向资金） |
| **热门概念** | newenergy, chip, tech, ai, ev | 新能源/芯片/科技/AI/新能源车 |

#### 使用示例

```bash
# 默认分析沪股通（hgt）
./daily_pool_analysis.sh

# 分析芯片板块
./daily_pool_analysis.sh chip

# 分析新能源板块
./daily_pool_analysis.sh newenergy

# 分析创业板
./daily_pool_analysis.sh cyb

# 分析沪深300
./daily_pool_analysis.sh hs300
```

#### 脚本功能

1. **潜力股发现** - 从指定股票池筛选 Top 20（得分 >= 15）
2. **自选股分析** - 分析 `watchlist.txt` 中的股票（如果存在）
3. **生成报告** - 输出 Excel 表格和技术分析图表

#### 配置说明

脚本内可调参数（编辑脚本修改）：

```bash
MIN_SCORE=15          # 最低分数阈值
TOP_N=20              # 显示前 N 名
START_DATE=...        # 默认最近1年数据
```

#### 输出文件

```
output/
  discover_<pool>_<日期>.xlsx       # 股票池筛选结果
  screen_<日期>.xlsx                # 自选股分析结果
  *_discover.png                    # 潜力股技术分析图表
  *_screen.png                      # 自选股技术分析图表
```

#### 定时任务设置

可使用 cron 设置每日自动执行（例如每天晚上9点）：

```bash
# 编辑 crontab
crontab -e

# 添加定时任务
0 21 * * 1-5 cd /path/to/AI_St && ./daily_pool_analysis.sh chip >> logs/daily_chip.log 2>&1
```

### 其他自动化脚本

- **daily_analysis.sh** - 创业板分析（固定池）
- **daily_analysis_watchlist.sh** - 仅自选股分析

---

## 技术分析图表说明

`screen` 和 `discover` 生成的图表包含三个子图：

```
┌─────────────────────────────────────────────┐
│  价格 + 均线                                  │
│  黑线=收盘价  蓝=MA5  橙=MA20  红虚线=MA60    │
│                          右上角: 触发的信号列表 │
├─────────────────────────────────────────────┤
│  成交量                                       │
│  绿柱=收阳  红柱=收阴  橙线=20日均量           │
├─────────────────────────────────────────────┤
│  MACD                                         │
│  蓝线=MACD  橙线=Signal  柱状图=Histogram      │
└─────────────────────────────────────────────┘
```

---

## 实用技巧

### 建议的日期范围

- 技术筛选至少需要 **60 个交易日** 的数据（约 3 个月）
- 建议使用 **6-9 个月** 的范围，兼顾趋势判断和指标准确性
- 示例：`--start 2025-07-01 --end 2026-04-08`

### 大池子加速

筛选 500 只股票（如中证 500）耗时较长，建议：

```bash
# 先快速看排名，不生成图表
stock discover --pool zz500 --start 2025-07-01 --end 2026-04-08 --no-chart --top 20

# 找到感兴趣的股票后，单独生成图表
stock screen 300677.SZ 300308.SZ --start 2025-07-01 --end 2026-04-08
```

### 组合使用工作流

```bash
# Step 1: 用 discover 从大池子找候选
stock discover --pool hs300 --start 2025-07-01 --end 2026-04-08 --no-chart --top 20

# Step 2: 挑出感兴趣的用 screen 详细分析
stock screen 600887.SS 601288.SS 300677.SZ --start 2025-07-01 --end 2026-04-08

# Step 3: 用 query 获取单只股票完整数据
stock query 300677.SZ --start 2024-01-01 --end 2026-04-08
```

---

## 项目结构

```
stock_cli/
  main.py              # CLI 入口 (query/screen/discover 命令)
  fetcher.py           # 数据获取 (yfinance)
  plotter.py           # 图表绘制 (收盘价图 + 技术分析三子图)
  exporter.py          # Excel 导出
  indicators.py        # 技术指标计算 (MA/RSI/MACD/ATR等)
  screener.py          # 评分系统 + 批量筛选
  screen_formatter.py  # 终端表格 + 筛选结果Excel导出
  pool_provider.py     # 股票池获取 (akshare + 静态fallback)
  data/                # 静态股票池文件 (sz50/hs300/cyb)
output/                # 所有输出文件 (图表/Excel)
```

## 常见问题

### 1. `stock` 命令不存在？
确保已激活 conda 环境并执行了 `pip install -e .`：
```bash
conda activate stock_cli
pip install -e .
```

### 2. 图表中文显示为方框？
程序已自动配置中文字体（macOS: Heiti TC，其他系统会按 Hiragino Sans GB / Arial Unicode MS / SimHei 顺序回退）。如仍有问题，请安装中文字体。

### 3. akshare 获取板块数据失败？
东方财富部分接口可能因网络问题失败，程序会自动回退到内置静态股票池文件 (`stock_cli/data/*.txt`)。预置的 sz50/hs300/zz500/cyb 不受影响。

### 4. yfinance 获取 A 股数据慢/失败？
A股代码必须带后缀：`.SS` (上证) 或 `.SZ` (深证)。如 `600519.SS`。网络不通时可考虑配置代理。
