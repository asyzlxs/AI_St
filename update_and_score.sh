#!/bin/bash
# ============================================================
#  股票池更新与跑分脚本
#  用法: ./update_and_score.sh
#  说明: 分析创业板指、沪股通、深股通 + 自选股，生成跑分报告
# ============================================================

set -e

# ===================== 配置区 ==============================

# conda 环境名
CONDA_ENV="stock_cli"

# 项目目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 自选股文件
WATCHLIST="${PROJECT_DIR}/watchlist.txt"

# 股票池列表和名称
POOLS=("cyb" "hgt" "sgt")
POOL_NAMES=("创业板指" "沪股通" "深股通")

# 获取股票池名称的函数
get_pool_name() {
    case "$1" in
        "cyb") echo "创业板指" ;;
        "hgt") echo "沪股通" ;;
        "sgt") echo "深股通" ;;
        *) echo "$1" ;;
    esac
}

# 时间范围: 最近 250 个交易日 (约 1 年)
END_DATE=$(date +%Y-%m-%d)
START_DATE=$(date -v-1y +%Y-%m-%d 2>/dev/null || date -d "1 year ago" +%Y-%m-%d)

# discover 参数
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
echo "  股票池更新与跑分  $(date '+%Y-%m-%d %H:%M')"
echo "  环境: ${CONDA_ENV} | Python: $(python --version 2>&1 | awk '{print $2}')"
echo "  范围: ${START_DATE} ~ ${END_DATE}"
echo "  分析池: 创业板指 + 沪股通 + 深股通 + 自选股"
echo "============================================================"
echo ""

cd "${PROJECT_DIR}"

# ===================== 分析各股票池 ========================

for pool in "${POOLS[@]}"; do
    pool_name=$(get_pool_name "$pool")

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  📊 分析 ${pool_name} (${pool})"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    echo "🔍 ${pool_name}潜力股发现 (Top ${TOP_N}, >= ${MIN_SCORE}分)"
    echo "------------------------------------------------------------"

    stock discover \
        --pool "${pool}" \
        --start "${START_DATE}" \
        --end "${END_DATE}" \
        --min-score "${MIN_SCORE}" \
        --top "${TOP_N}"

    echo ""
    echo "✅ ${pool_name} 分析完成"
    echo ""
done

# ===================== 自选股分析 ==========================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📋 分析自选股 (watchlist.txt)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -f "${WATCHLIST}" ]; then
    echo "🔍 自选股评分 (${WATCHLIST})"
    echo "------------------------------------------------------------"

    stock screen \
        --file "${WATCHLIST}" \
        --start "${START_DATE}" \
        --end "${END_DATE}"

    echo ""
    echo "✅ 自选股分析完成"
else
    echo "⚠️  跳过自选股分析 — 未找到 ${WATCHLIST}"
    echo "    创建方法: 每行一个代码，如 600519.SS"
fi

echo ""

# ===================== 汇总 ================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📁 输出文件汇总"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

OUTPUT_DIR="${PROJECT_DIR}/output"
if [ -d "${OUTPUT_DIR}" ]; then
    echo "  目录: ${OUTPUT_DIR}"
    echo ""
    echo "  今日生成的文件:"

    # 统计今日文件
    file_count=0
    find "${OUTPUT_DIR}" -type f \( -name "*.xlsx" -o -name "*.png" \) 2>/dev/null | \
        while read f; do
            # 只显示今天修改的文件
            file_date=$(date -r "$f" +%Y-%m-%d 2>/dev/null || stat -c %y "$f" 2>/dev/null | cut -d' ' -f1)
            if [ "$file_date" = "${END_DATE}" ]; then
                size=$(du -h "$f" | awk '{print $1}')
                echo "    ${size}  $(basename "$f")"
                ((file_count++)) || true
            fi
        done

    echo ""
    echo "  共生成 ${file_count} 个文件"
else
    echo "  ⚠️  输出目录不存在: ${OUTPUT_DIR}"
fi

echo ""
echo "============================================================"
echo "  🎉 全部分析完成!  $(date '+%H:%M:%S')"
echo "  📊 已完成: 创业板指 + 沪股通 + 深股通 + 自选股"
echo "  📁 报告位置: ${OUTPUT_DIR}/"
echo "============================================================"
