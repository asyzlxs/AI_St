# 自动化分析脚本使用指南

本项目提供了多个自动化脚本，用于每日股票分析和监控。

## 📋 脚本列表

| 脚本名称 | 功能 | 推荐使用场景 |
|---------|------|------------|
| **daily_pool_analysis.sh** | 通用股票池分析（支持参数） | ⭐ 推荐，最灵活 |
| daily_analysis.sh | 创业板分析（固定） | 仅需创业板分析 |
| daily_analysis_hgt.sh | 沪股通分析（固定） | 仅需沪股通分析 |
| daily_analysis_watchlist.sh | 自选股分析 | 仅分析自选股 |

## ⭐ 推荐：daily_pool_analysis.sh

### 特点
- ✅ 支持所有股票池（13个）
- ✅ 命令行参数灵活切换
- ✅ 默认沪股通（北向资金）
- ✅ 包含自选股分析

### 用法

```bash
./daily_pool_analysis.sh [POOL]
```

### 支持的股票池

**指数池**
```bash
./daily_pool_analysis.sh sz50      # 上证50
./daily_pool_analysis.sh hs300     # 沪深300
./daily_pool_analysis.sh zz500     # 中证500
./daily_pool_analysis.sh cyb       # 创业板指
```

**互联互通（北向资金）**
```bash
./daily_pool_analysis.sh hgt       # 沪股通（默认）
./daily_pool_analysis.sh sgt       # 深股通
```

**热门概念板块**
```bash
./daily_pool_analysis.sh newenergy # 新能源
./daily_pool_analysis.sh chip      # 芯片
./daily_pool_analysis.sh tech      # 科技创新
./daily_pool_analysis.sh ai        # 人工智能
./daily_pool_analysis.sh ev        # 新能源车
```

### 输出内容

1. **股票池分析** - 从指定股票池筛选 Top 20（得分 >= 15）
2. **自选股分析** - 分析 `watchlist.txt` 中的股票（可选）
3. **Excel 报告** - 完整的筛选结果和技术指标
4. **技术分析图表** - 价格+均线/成交量/MACD 三子图

### 输出文件位置

```
output/
  discover_<pool>_<日期>.xlsx       # 股票池筛选结果
  screen_<日期>.xlsx                # 自选股分析结果（如有）
  *_discover.png                    # 潜力股技术分析图表
  *_screen.png                      # 自选股技术分析图表
```

## 🔧 自定义配置

### 修改筛选参数

编辑脚本第 67-68 行：

```bash
MIN_SCORE=15          # 最低分数阈值 (0-100)
TOP_N=20              # 显示前 N 名
```

### 修改时间范围

默认分析最近 1 年数据。修改第 62-63 行：

```bash
END_DATE=$(date +%Y-%m-%d)
START_DATE=$(date -v-6m +%Y-%m-%d)    # 改为最近 6 个月
```

### 添加自选股

创建 `watchlist.txt` 文件，每行一个股票代码：

```text
# 我的自选股
600519.SS    # 贵州茅台
300750.SZ    # 宁德时代
AAPL         # 苹果
0700.HK      # 腾讯
```

## ⏰ 设置定时任务

### 方式一：cron（Linux/macOS）

```bash
# 编辑 crontab
crontab -e

# 每周一到周五晚上 9 点执行
0 21 * * 1-5 cd /path/to/AI_St && ./daily_pool_analysis.sh chip >> logs/chip.log 2>&1

# 每天早上 8 点分析沪股通
0 8 * * * cd /path/to/AI_St && ./daily_pool_analysis.sh hgt >> logs/hgt.log 2>&1
```

### 方式二：launchd（macOS）

创建 `~/Library/LaunchAgents/com.stock.analysis.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stock.analysis</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/AI_St/daily_pool_analysis.sh</string>
        <string>chip</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>21</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</dict>
</plist>
```

加载任务：
```bash
launchctl load ~/Library/LaunchAgents/com.stock.analysis.plist
```

## 📊 使用场景示例

### 场景 1: 每日监控沪股通

```bash
# 每天执行一次，查看北向资金青睐的股票
./daily_pool_analysis.sh hgt
```

### 场景 2: 周末全面扫描

```bash
# 周末扫描多个板块
./daily_pool_analysis.sh chip
./daily_pool_analysis.sh newenergy
./daily_pool_analysis.sh ai
```

### 场景 3: 结合自选股

```bash
# 1. 维护 watchlist.txt 添加关注的股票
# 2. 每天执行分析
./daily_pool_analysis.sh hgt

# 脚本会同时分析：
# - 沪股通 Top 20
# - watchlist.txt 中的所有股票
```

### 场景 4: 行业轮动监控

```bash
# 分别监控不同行业，找机会
./daily_pool_analysis.sh chip        # 芯片板块
./daily_pool_analysis.sh newenergy   # 新能源板块
./daily_pool_analysis.sh ev          # 新能源车
```

## 🎯 最佳实践

### 1. 定期执行
- 每天收盘后执行（晚上8-9点）
- 避免开盘时段（数据可能不完整）

### 2. 合理设置阈值
- **MIN_SCORE=15**: 宽松筛选，候选更多
- **MIN_SCORE=25**: 中等筛选，信号较强
- **MIN_SCORE=35**: 严格筛选，高质量信号

### 3. 结合多个池
- 从大池子找方向（如 hs300）
- 在小池子找个股（如 chip）
- 用自选股跟踪（watchlist.txt）

### 4. 日志管理
```bash
# 创建日志目录
mkdir -p logs

# 执行时保存日志
./daily_pool_analysis.sh chip 2>&1 | tee logs/chip_$(date +%Y%m%d).log
```

## ❓ 常见问题

### Q: 脚本执行很慢？
A: 大池子（如沪股通 1300+ 只）需要较长时间，可以：
- 添加 `--no-chart` 参数跳过图表生成（需修改脚本）
- 减少 `TOP_N` 数量
- 使用较小的股票池

### Q: 如何只分析股票池，不分析自选股？
A: 删除或重命名 `watchlist.txt` 文件

### Q: 如何同时监控多个板块？
A: 写一个简单的包装脚本：
```bash
#!/bin/bash
for pool in chip newenergy ai; do
    ./daily_pool_analysis.sh $pool
done
```

### Q: conda 环境激活失败？
A: 确保：
1. 已安装 conda
2. 环境名为 `stock_cli`
3. 或修改脚本中的 `CONDA_ENV` 变量

## 📝 脚本对比

| 特性 | daily_pool_analysis.sh | daily_analysis.sh | daily_analysis_hgt.sh |
|-----|----------------------|------------------|---------------------|
| 支持参数 | ✅ 是 | ❌ 否 | ❌ 否 |
| 股票池数量 | 13 个 | 1 个（创业板） | 1 个（沪股通） |
| 灵活性 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| 推荐使用 | ✅ 是 | 向后兼容 | 向后兼容 |
