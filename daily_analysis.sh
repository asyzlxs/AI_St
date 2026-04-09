#!/bin/bash
# ============================================================
#  每日股票分析脚本
#  用法: ./daily_analysis.sh
#  说明: 分析创业板 Top 20 + 自选股，生成报告和图表
# ============================================================

set -e

# ===================== 配置区 (按需修改) =====================

# conda 环境名
CONDA_ENV="stock_cli"

# 项目目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 自选股文件
WATCHLIST="${PROJECT_DIR}/watchlist.txt"

# 时间范围: 最近 250 个交易日 (约 1 年)
END_DATE=$(date +%Y-%m-%d)
START_DATE=$(date -v-1y +%Y-%m-%d 2>/dev/null || date -d "1 year ago" +%Y-%m-%d)

# discover 参数
POOL="cyb"            # 股票池: sz50 / hs300 / zz500 / cyb
MIN_SCORE=15          # 最低分数阈值
TOP_N=20              # 显示前 N 名

# ===================== 初始化 ==============================

# 激活 conda
CONDA_BASE=$(conda info --base 2>/dev/null)
if [ -z "$CONDA_BASE" ]; then
    echo "❌ 未找到 conda，请先安装 Anaconda 或 Miniconda"
    exit 1
fi
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV}"

echo "============================================================"
echo "  每日股票分析  $(date '+%Y-%m-%d %H:%M')"
echo "  环境: ${CONDA_ENV} | Python: $(python --version 2>&1 | awk '{print $2}')"
echo "  范围: ${START_DATE} ~ ${END_DATE}"
echo "============================================================"
echo ""

cd "${PROJECT_DIR}"

# ===================== Step 1: 创业板潜力股发现 ==============

echo "📊 [1/3] 创业板潜力股发现 (${POOL}, Top ${TOP_N}, >= ${MIN_SCORE}分)"
echo "------------------------------------------------------------"

stock discover \
    --pool "${POOL}" \
    --start "${START_DATE}" \
    --end "${END_DATE}" \
    --min-score "${MIN_SCORE}" \
    --top "${TOP_N}"

echo ""

# ===================== Step 2: 自选股/持仓分析 ===============

if [ -f "${WATCHLIST}" ]; then
    echo "📋 [2/3] 自选股分析 (${WATCHLIST})"
    echo "------------------------------------------------------------"

    stock screen \
        --file "${WATCHLIST}" \
        --start "${START_DATE}" \
        --end "${END_DATE}"
else
    echo "⚠️  [2/3] 跳过自选股分析 — 未找到 ${WATCHLIST}"
    echo "    创建方法: 每行一个代码，如 600519.SS"
fi

echo ""

# ===================== Step 3: 汇总 ==========================

echo "📁 [3/3] 输出文件汇总"
echo "------------------------------------------------------------"

OUTPUT_DIR="${PROJECT_DIR}/output"
if [ -d "${OUTPUT_DIR}" ]; then
    echo "  目录: ${OUTPUT_DIR}"
    echo ""
    echo "  今日生成的文件:"
    find "${OUTPUT_DIR}" -type f -name "*.xlsx" -o -name "*.png" | \
        while read f; do
            # 只显示今天修改的文件
            if [ "$(date -r "$f" +%Y-%m-%d 2>/dev/null || stat -c %y "$f" 2>/dev/null | cut -d' ' -f1)" = "${END_DATE}" ]; then
                size=$(du -h "$f" | awk '{print $1}')
                echo "    ${size}  $(basename "$f")"
            fi
        done
fi

echo ""
echo "============================================================"
echo "  分析完成!  $(date '+%H:%M:%S')"
echo "  Excel 和图表在: ${OUTPUT_DIR}/"
echo "============================================================"
