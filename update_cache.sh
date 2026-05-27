#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

END_DATE="${1:-$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)}"
START_DATE=$(date -v-1y +%Y-%m-%d 2>/dev/null || date -d "1 year ago" +%Y-%m-%d)

POOLS=("cyb" "hgt" "sgt")

cd "${PROJECT_DIR}"

if ! command -v stock >/dev/null 2>&1; then
    echo "❌ 未找到 stock 命令，请先在当前 Python 环境执行：python -m pip install -e ${PROJECT_DIR}"
    exit 1
fi

echo "============================================================"
echo "  数据缓存更新  $(date '+%Y-%m-%d %H:%M')"
echo "  范围: ${START_DATE} ~ ${END_DATE}"
echo "============================================================"
echo ""

for POOL in "${POOLS[@]}"; do
    echo "🧱 更新缓存 (${POOL})"
    echo "------------------------------------------------------------"

    stock update-cache \
        --pool "${POOL}" \
        --start "${START_DATE}" \
        --end "${END_DATE}"

    echo ""
done

echo "============================================================"
echo "  缓存更新完成!  $(date '+%H:%M:%S')"
echo "============================================================"
