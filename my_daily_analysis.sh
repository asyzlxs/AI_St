#!/bin/bash
# ============================================================
#  我的专属每日股票分析脚本
#  用法: ./my_daily_analysis.sh
#  说明: 依次分析创业板(cyb)、沪港通(hgt)、深港通(sgt)，以及我的自选股(watchlist)
# ============================================================

set -e

# ===================== 配置区 (按需修改) =====================

# 项目目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 自选股文件
WATCHLIST="${PROJECT_DIR}/watchlist.txt"

# 时间范围: 最近 250 个交易日 (约 1 年)
# 可传入结束日期参数，默认取昨天（缓存数据通常 T+1 才稳定）
END_DATE="${1:-$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)}"
START_DATE=$(date -v-1y +%Y-%m-%d 2>/dev/null || date -d "1 year ago" +%Y-%m-%d)

# discover 参数
POOLS=("cyb" "hgt" "sgt")
MIN_SCORE=15          # 最低分数阈值
TOP_N=20              # 显示前 N 名

# ===================== 初始化 ==============================

echo "============================================================"
echo "  专属每日股票分析  $(date '+%Y-%m-%d %H:%M')"
echo "  Python: $(python --version 2>&1 | awk '{print $2}')"
echo "  范围: ${START_DATE} ~ ${END_DATE}"
echo "============================================================"
echo ""

cd "${PROJECT_DIR}"

if ! command -v stock >/dev/null 2>&1; then
    echo "❌ 未找到 stock 命令，请先在当前 Python 环境执行：python -m pip install -e ${PROJECT_DIR}"
    exit 1
fi

# ===================== Step 1: 各大板块潜力股发现 ==============

for POOL in "${POOLS[@]}"; do
    echo "📊 潜力股发现 (${POOL}, Top ${TOP_N}, >= ${MIN_SCORE}分)"
    echo "------------------------------------------------------------"

    stock discover \
        --pool "${POOL}" \
        --start "${START_DATE}" \
        --end "${END_DATE}" \
        --min-score "${MIN_SCORE}" \
        --top "${TOP_N}"

    echo ""
done

# ===================== Step 2: 自选股/持仓分析 ===============

if [ -f "${WATCHLIST}" ]; then
    echo "📋 自选股分析 (${WATCHLIST})"
    echo "------------------------------------------------------------"

    stock screen \
        --file "${WATCHLIST}" \
        --start "${START_DATE}" \
        --end "${END_DATE}"
else
    echo "⚠️  跳过自选股分析 — 未找到 ${WATCHLIST}"
    echo "    创建方法: 每行一个代码，如 600519.SS"
fi

echo ""

# ===================== Step 3: 汇总 ==========================

echo "📁 输出文件汇总"
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
echo "  所有分析完成!  $(date '+%H:%M:%S')"
echo "  Excel 和图表在: ${OUTPUT_DIR}/"
echo "============================================================"
