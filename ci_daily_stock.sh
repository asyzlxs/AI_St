#!/usr/bin/env bash
set -euo pipefail

die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "缺少命令: $1"
}

is_weekday() {
  local dow
  dow="$(date +%u)"
  [[ "$dow" -ge 1 && "$dow" -le 5 ]]
}

ensure_git_identity() {
  local name email
  name="$(git config user.name || true)"
  email="$(git config user.email || true)"
  if [[ -z "${name}" ]]; then
    git config user.name "${GIT_AUTHOR_NAME:-ci-bot}"
  fi
  if [[ -z "${email}" ]]; then
    git config user.email "${GIT_AUTHOR_EMAIL:-ci-bot@example.com}"
  fi
}

checkout_target_branch() {
  git fetch --quiet origin solo_main || true
  if git show-ref --verify --quiet refs/remotes/origin/solo_main; then
    git checkout -B solo_main origin/solo_main >/dev/null 2>&1 || die "无法切换到 origin/solo_main"
  else
    git checkout -B solo_main >/dev/null 2>&1 || die "无法创建本地分支 solo_main"
  fi
}

safe_git_push() {
  local out
  if ! out="$(GIT_TERMINAL_PROMPT=0 git push --quiet origin HEAD:refs/heads/solo_main 2>&1)"; then
    printf '%s\n' "$out" | sed -E 's#(https?://)[^/@]+@#\1***@#g' >&2
    die "git push 失败"
  fi
}

main() {
  cd /workspace
  require_cmd git
  require_cmd python3
  require_cmd date
  require_cmd find
  require_cmd xargs

  if ! is_weekday; then
    echo "非工作日，跳过执行"
    exit 0
  fi

  if [[ ! -f /workspace/requirements.txt ]]; then
    die "缺少 /workspace/requirements.txt"
  fi
  if [[ ! -f /workspace/setup.py ]]; then
    die "缺少 /workspace/setup.py"
  fi

  checkout_target_branch
  ensure_git_identity

  python3 -m pip --version >/dev/null 2>&1 || die "pip 不可用 (python3 -m pip)"

  python3 -m pip install --upgrade pip >/dev/null 2>&1 || die "pip 升级失败"
  python3 -m pip install -r /workspace/requirements.txt >/dev/null 2>&1 || die "依赖安装失败 (requirements.txt)"
  python3 -m pip install -e /workspace >/dev/null 2>&1 || die "安装 stock-cli 失败 (pip install -e /workspace)"

  require_cmd stock

  local end_date start_date
  end_date="$(date -d "yesterday" +%Y-%m-%d)"
  start_date="$(date -d "1 year ago" +%Y-%m-%d)"

  mkdir -p /workspace/output

  stock discover --pool cyb --start "${start_date}" --end "${end_date}" --min-score 15 --top 20
  stock discover --pool hgt --start "${start_date}" --end "${end_date}" --min-score 15 --top 20
  stock discover --pool sgt --start "${start_date}" --end "${end_date}" --min-score 15 --top 20

  if [[ -f /workspace/watchlist.txt ]]; then
    stock screen --file /workspace/watchlist.txt --start "${start_date}" --end "${end_date}"
  else
    echo "未找到 /workspace/watchlist.txt，跳过自选股分析"
  fi

  local files_count
  files_count="$(find /workspace/output -type f \( -name "*.xlsx" -o -name "*.png" \) -mmin -240 -print0 | xargs -0 -r -I {} echo {} | wc -l | tr -d ' ')"
  if [[ "${files_count}" -eq 0 ]]; then
    echo "近 4 小时内无新增/更新的 output 产物，跳过提交与推送"
    exit 0
  fi

  find /workspace/output -type f \( -name "*.xlsx" -o -name "*.png" \) -mmin -240 -print0 | xargs -0 -r git add -f --

  if git diff --cached --quiet; then
    echo "暂存区无变化，跳过提交与推送"
    exit 0
  fi

  git commit -m "chore: daily stock report ${end_date}" >/dev/null 2>&1 || die "git commit 失败"
  safe_git_push
  echo "已提交并推送到 origin/solo_main"
}

main "$@"
