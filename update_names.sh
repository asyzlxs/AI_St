#!/bin/bash
# ============================================================
#  更新 A 股名称映射缓存脚本
#  用法: ./update_names.sh
#  说明: 请在【关闭外网 VPN】的情况下执行此脚本，用于本地缓存股票中文名称
# ============================================================

set -e

# ===================== 配置区 =====================

# conda 环境名
CONDA_ENV="stock_cli"

# 项目目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ===================== 执行 ==============================

# 激活 conda
CONDA_BASE=$(conda info --base 2>/dev/null)
if [ -z "$CONDA_BASE" ]; then
    echo "❌ 未找到 conda，请先安装 Anaconda 或 Miniconda"
    exit 1
fi
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV}"

echo "============================================================"
echo "  更新 A 股股票名称本地缓存  $(date '+%Y-%m-%d %H:%M')"
echo "============================================================"
echo ""

cd "${PROJECT_DIR}"

python "${PROJECT_DIR}/update_stock_names.py"

echo ""
echo "============================================================"
echo "  执行完毕!"
echo "  现在你可以【开启外网 VPN】并运行 daily_analysis.sh 脚本了"
echo "============================================================"
