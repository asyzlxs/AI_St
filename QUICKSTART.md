# 快速开始指南

## 🚀 30秒开始使用

```bash
# 1. 激活环境
conda activate stock_cli

# 2. 运行自动化分析（推荐）
./daily_pool_analysis.sh

# 完成！查看 output/ 目录下的报告
```

## 📋 股票池速查表

| 代码 | 名称 | 股票数 | 说明 |
|------|------|--------|------|
| **hgt** | 沪股通 | 1300+ | 北向资金持仓，默认 ⭐ |
| **sgt** | 深股通 | 800+ | 北向资金持仓 |
| **chip** | 芯片 | 200+ | 半导体产业链 |
| **newenergy** | 新能源 | 300+ | 光伏/风电/储能 |
| **ai** | 人工智能 | 150+ | AI算法/算力 |
| **ev** | 新能源车 | 250+ | 整车/电池 |
| **sz50** | 上证50 | 50 | 上交所龙头 |
| **hs300** | 沪深300 | 300 | 主板蓝筹 |
| **cyb** | 创业板 | 100 | 创新成长 |

## 🎯 常用命令

### 自动化脚本（推荐）

```bash
# 沪股通分析（默认）
./daily_pool_analysis.sh

# 芯片板块
./daily_pool_analysis.sh chip

# 新能源板块
./daily_pool_analysis.sh newenergy

# 多板块扫描
./multi_pool_analysis.sh
```

### 手动命令

```bash
# 发现潜力股
stock discover --pool hgt --start 2025-07-01 --end 2026-04-13

# 筛选自选股
stock screen 600519.SS 300750.SZ --start 2025-07-01 --end 2026-04-13

# 查询单股
stock query AAPL --start 2025-01-01 --end 2026-04-13

# 回测验证
stock backtest --pool chip --start 2024-04-08 --end 2026-04-08
```

## 📁 输出文件

所有输出在 `output/` 目录：

```
output/
├── discover_hgt_2026-04-13.xlsx      # 沪股通筛选结果
├── screen_2026-04-13.xlsx            # 自选股分析结果
├── 600519_SS_2026-04-13_discover.png # 技术分析图表
└── ...
```

## 💡 推荐工作流

### 日常监控（每天）
```bash
./daily_pool_analysis.sh hgt
```

### 周末扫描（每周）
```bash
./multi_pool_analysis.sh
```

### 深度研究（按需）
```bash
# 1. 发现候选
stock discover --pool chip --start 2025-07-01 --end 2026-04-13 --top 30

# 2. 筛选重点
stock screen 600276.SS 688981.SS --start 2025-07-01 --end 2026-04-13

# 3. 详细查看
stock query 600276.SS --start 2024-01-01 --end 2026-04-13
```

## 🔧 自定义配置

### 添加自选股
创建 `watchlist.txt`：
```text
600519.SS    # 贵州茅台
300750.SZ    # 宁德时代
```

### 调整筛选参数
编辑 `daily_pool_analysis.sh`：
```bash
MIN_SCORE=25    # 提高到 25 分（更严格）
TOP_N=15        # 只看前 15 名
```

### 设置定时任务
```bash
# 编辑 crontab
crontab -e

# 每天晚上 9 点执行
0 21 * * * cd /path/to/AI_St && ./daily_pool_analysis.sh chip
```

## 📖 更多信息

- **完整文档**: [README.md](README.md)
- **脚本指南**: [SCRIPTS.md](SCRIPTS.md)
- **股票池详解**: [POOLS.md](POOLS.md)
- **更新日志**: [CHANGELOG.md](CHANGELOG.md)

## ❓ 常见问题

**Q: 脚本执行很慢？**
A: 大池子需要时间，可以减少 TOP_N 或使用较小的池

**Q: conda 命令不存在？**
A: 安装 Anaconda 或 Miniconda

**Q: 图表中文乱码？**
A: 已自动配置，如仍有问题请安装中文字体

**Q: 如何只分析股票池？**
A: 删除 `watchlist.txt` 文件

## 🎓 学习路径

1. **新手**: 直接运行 `./daily_pool_analysis.sh`
2. **进阶**: 尝试不同股票池参数
3. **高级**: 使用手动命令精细控制
4. **专家**: 修改脚本和筛选逻辑

---

**开始使用**: `./daily_pool_analysis.sh` 🚀