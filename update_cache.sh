#!/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

END_DATE="${1:-$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)}"
START_DATE=$(date -v-1y +%Y-%m-%d 2>/dev/null || date -d "1 year ago" +%Y-%m-%d)

cd "${PROJECT_DIR}"

if ! command -v stock >/dev/null 2>&1; then
    echo "❌ 未找到 stock 命令，请先在当前 Python 环境执行：python -m pip install -e ${PROJECT_DIR}"
    exit 1
fi

run_update_cache() {
  local label="$1"
  shift

  echo "============================================================"
  echo "  数据缓存更新: ${label}  $(date '+%Y-%m-%d %H:%M')"
  echo "  范围: ${START_DATE} ~ ${END_DATE}"
  echo "============================================================"
  echo ""

  local tmp
  tmp="$(mktemp)"
  set +e
  stock update-cache "$@" --start "${START_DATE}" --end "${END_DATE}" 2>&1 | tee "${tmp}"
  local rc="${PIPESTATUS[0]}"
  set -e

  if [ "${rc}" -ne 0 ]; then
    echo "❌ 错误: stock update-cache 执行失败（${label}），退出码: ${rc}" >&2
    rm -f "${tmp}"
    exit "${rc}"
  fi

  if grep -q "更新失败:" "${tmp}"; then
    echo "❌ 错误: stock update-cache 存在失败条目（${label}），请查看日志定位具体股票" >&2
    rm -f "${tmp}"
    exit 1
  fi

  rm -f "${tmp}"
  echo ""
}

run_update_cache "创业板" --pool cyb
run_update_cache "沪股通" --pool hgt
run_update_cache "深股通" --pool sgt

WATCHLIST="${PROJECT_DIR}/watchlist.txt"
if [ -f "${WATCHLIST}" ]; then
  symbols="$(grep -v '^[[:space:]]*#' "${WATCHLIST}" | awk '{print $1}' | tr '\n' ' ' | xargs || true)"
  if [ -n "${symbols}" ]; then
    run_update_cache "自选股" ${symbols}
  fi
fi
