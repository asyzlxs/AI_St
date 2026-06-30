#!/usr/bin/env bash
# 历史得分回溯分析
#
# 用法示例:
#   ./run_backtest.sh                                     # 默认：cyb，首次穿越模式
#   ./run_backtest.sh --pools cyb,hgt,sgt                 # 三个池各出一个 Excel
#   ./run_backtest.sh --pools hs300 --mode cooldown       # 冷却期模式
#   ./run_backtest.sh --pools cyb --score-thresholds 20,30,40,50,60,80
#   ./run_backtest.sh --pools sgt --horizons 5,10,20 --workers 16

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v conda &>/dev/null; then
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate stock_cli 2>/dev/null || true
fi

echo "========================================"
echo "  历史得分回溯分析"
echo "========================================"

python backtest_score/backtest_score.py "$@"
