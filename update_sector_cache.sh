#!/usr/bin/env bash
# ============================================================
#  行业分类缓存预取（一次性执行）
#  用法:
#    ./update_sector_cache.sh           # 默认 16 线程，跳过已有缓存
#    ./update_sector_cache.sh 32        # 指定 32 线程
#    ./update_sector_cache.sh 16 force  # 强制重新拉取全部
# ============================================================

set -euo pipefail

CONDA_ENV="stock_cli"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKERS="${1:-8}"
FORCE="${2:-}"

CONDA_BASE=$(conda info --base 2>/dev/null)
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV}"

cd "${PROJECT_DIR}"

echo "============================================================"
echo "  行业分类缓存预取"
echo "  线程数: ${WORKERS}"
echo "============================================================"

FORCE_FLAG=""
if [ "${FORCE}" = "force" ]; then
    FORCE_FLAG="--force"
    echo "  模式: 强制重新拉取全部"
else
    echo "  模式: 仅拉取缺失条目"
fi

echo ""

python update_sector_cache.py --workers "${WORKERS}" ${FORCE_FLAG}
