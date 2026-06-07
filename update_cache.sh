#!/bin/bash
# ============================================================
#  股票数据缓存更新脚本
#  用法: ./update_cache.sh [START_DATE]
#  说明: 每天凌晨运行，增量更新 cyb/hgt/sgt 板块及自选股缓存
#        START_DATE 默认 2025-01-01，可传入覆盖
# ============================================================

set -e

# ===================== 配置区 ==============================

CONDA_ENV="stock_cli"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
WATCHLIST="${PROJECT_DIR}/watchlist.txt"
LOG_DIR="${PROJECT_DIR}/logs"
START_DATE="${1:-2025-01-01}"
END_DATE=$(date +%Y-%m-%d)
LOG_FILE="${LOG_DIR}/update_cache_${END_DATE}.log"

POOLS=("cyb" "hgt" "sgt")

# ===================== 初始化 ==============================

mkdir -p "${LOG_DIR}"

# 所有输出同时写入日志文件
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "============================================================"
echo "  缓存更新开始  $(date '+%Y-%m-%d %H:%M:%S')"
echo "  范围: ${START_DATE} ~ ${END_DATE}"
echo "============================================================"
echo ""

# 激活 conda
CONDA_BASE=$(conda info --base 2>/dev/null)
if [ -z "$CONDA_BASE" ]; then
    echo "错误: 未找到 conda，请先安装 Anaconda 或 Miniconda"
    exit 1
fi
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV}"

echo "环境: ${CONDA_ENV} | Python: $(python --version 2>&1 | awk '{print $2}')"
echo ""

cd "${PROJECT_DIR}"

# ===================== 更新各板块缓存 ======================

SUCCESS=0
FAIL=0

for pool in "${POOLS[@]}"; do
    echo "------------------------------------------------------------"
    echo "  更新板块缓存: ${pool}"
    echo "------------------------------------------------------------"

    if stock update-cache --pool "${pool}" --start "${START_DATE}" --end "${END_DATE}"; then
        echo "  [OK] ${pool} 缓存更新完成"
        ((SUCCESS++)) || true
    else
        echo "  [FAIL] ${pool} 缓存更新失败"
        ((FAIL++)) || true
    fi
    echo ""
done

# ===================== 更新自选股缓存 ======================

if [ -f "${WATCHLIST}" ]; then
    echo "------------------------------------------------------------"
    echo "  更新自选股缓存 (watchlist.txt)"
    echo "------------------------------------------------------------"

    # 读取自选股代码（过滤注释行和空行）
    SYMBOLS=$(grep -v '^\s*#' "${WATCHLIST}" | grep -v '^\s*$' | tr '\n' ' ')

    if [ -n "${SYMBOLS}" ]; then
        if stock update-cache ${SYMBOLS} --start "${START_DATE}" --end "${END_DATE}"; then
            echo "  [OK] 自选股缓存更新完成"
            ((SUCCESS++)) || true
        else
            echo "  [FAIL] 自选股缓存更新失败"
            ((FAIL++)) || true
        fi
    else
        echo "  watchlist.txt 中没有有效的股票代码，跳过"
    fi
    echo ""
fi

# ===================== 汇总 ================================

CACHE_DIR="${PROJECT_DIR}/stock_cli/data/cache"
CACHE_COUNT=0
if [ -d "${CACHE_DIR}" ]; then
    CACHE_COUNT=$(find "${CACHE_DIR}" -name "*.csv" | wc -l | tr -d ' ')
fi

echo "============================================================"
echo "  缓存更新完成  $(date '+%Y-%m-%d %H:%M:%S')"
echo "  成功: ${SUCCESS} 组 | 失败: ${FAIL} 组"
echo "  本地缓存文件数: ${CACHE_COUNT} 只股票"
echo "  日志: ${LOG_FILE}"
echo "============================================================"
