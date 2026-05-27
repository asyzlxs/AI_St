#!/usr/bin/env bash
set -euo pipefail

on_err() {
  local exit_code=$?
  local line_no=${BASH_LINENO[0]:-}
  local cmd=${BASH_COMMAND:-}
  printf '❌ 失败: exit=%s line=%s cmd=%s\n' "$exit_code" "$line_no" "$cmd" >&2
  exit "$exit_code"
}
trap on_err ERR

die() {
  printf '❌ %s\n' "$1" >&2
  exit 1
}

sanitize() {
  sed -E 's#(https?://)[^/@]+@#\1***@#g'
}

run_git_quiet() {
  local out
  if ! out="$("$@" 2>&1)"; then
    printf '%s\n' "$out" | sanitize >&2
    return 1
  fi
}

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

export CI="${CI:-true}"
export GIT_TERMINAL_PROMPT=0

dow="$(date +%u)"
if [[ "$dow" == "6" || "$dow" == "7" ]]; then
  printf 'ℹ️  周末跳过报表生成与提交\n'
  exit 0
fi

run_git_quiet git rev-parse --is-inside-work-tree >/dev/null || die "当前目录不是 git 仓库: ${PROJECT_DIR}"
run_git_quiet git remote get-url origin >/dev/null || die "未配置 git remote: origin"

if git ls-remote --exit-code --heads origin solo_main >/dev/null 2>&1; then
  run_git_quiet git fetch --prune origin solo_main
  run_git_quiet git checkout -B solo_main FETCH_HEAD
else
  run_git_quiet git checkout -B solo_main
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "未找到 python3（或通过 PYTHON_BIN 指定的解释器）"

VENV_DIR="${VENV_DIR:-${TMPDIR:-/tmp}/stock_cli_venv}"
if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  rm -rf "$VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR" || die "创建虚拟环境失败: ${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"

python -m pip install -U pip setuptools wheel >/dev/null
python -m pip install -r "${PROJECT_DIR}/requirements.txt"
python -m pip install -e "${PROJECT_DIR}"

command -v stock >/dev/null 2>&1 || die "stock 命令不可用：请检查依赖是否安装成功（pip install -e .）"

END_DATE="${END_DATE:-$(date -d "yesterday" +%Y-%m-%d)}"
START_DATE="${START_DATE:-$(date -d "${END_DATE} -1 year" +%Y-%m-%d)}"
MIN_SCORE="${MIN_SCORE:-15}"
TOP_N="${TOP_N:-20}"
POOLS_CSV="${POOLS_CSV:-cyb,hgt,sgt}"
WATCHLIST="${WATCHLIST:-${PROJECT_DIR}/watchlist.txt}"

IFS=',' read -r -a POOLS <<<"$POOLS_CSV"

printf '============================================================\n'
printf '  CI 每日股票报表  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')"
printf '  Python: %s\n' "$(python --version 2>&1)"
printf '  范围: %s ~ %s\n' "$START_DATE" "$END_DATE"
printf '============================================================\n'

for pool in "${POOLS[@]}"; do
  printf '\n📊 潜力股发现: %s (Top %s, >= %s)\n' "$pool" "$TOP_N" "$MIN_SCORE"
  stock discover --pool "$pool" --start "$START_DATE" --end "$END_DATE" --min-score "$MIN_SCORE" --top "$TOP_N"
done

if [[ -f "$WATCHLIST" ]]; then
  printf '\n📋 自选股筛选: %s\n' "$WATCHLIST"
  stock screen --file "$WATCHLIST" --start "$START_DATE" --end "$END_DATE"
else
  printf '\nℹ️  未找到 watchlist，跳过自选股筛选: %s\n' "$WATCHLIST"
fi

OUTPUT_DIR="${PROJECT_DIR}/output"
mkdir -p "$OUTPUT_DIR"

mapfile -t artifacts < <(find "$OUTPUT_DIR" -type f \( -name "*.xlsx" -o -name "*.png" \) -mmin -240 -print 2>/dev/null || true)

if [[ ${#artifacts[@]} -eq 0 ]]; then
  printf '\nℹ️  output/ 下近 4 小时无新增/更新的 .xlsx/.png，跳过提交\n'
  exit 0
fi

printf '\n📦 近 4 小时产物（将强制暂存）:\n'
for f in "${artifacts[@]}"; do
  printf '  - %s\n' "${f#${PROJECT_DIR}/}"
done

run_git_quiet git add -f -- "${artifacts[@]}"

if git diff --cached --quiet; then
  printf '\nℹ️  暂存区无变更，跳过提交\n'
  exit 0
fi

git config user.email >/dev/null 2>&1 || git config user.email "ci@local"
git config user.name >/dev/null 2>&1 || git config user.name "ci"

run_git_quiet git commit -m "ci: daily stock report $(date +%F)"

if ! out="$(git push -q origin solo_main 2>&1)"; then
  printf '%s\n' "$out" | sanitize >&2
  die "git push 失败"
fi

printf '\n✅ 已提交并推送到 origin/solo_main\n'
