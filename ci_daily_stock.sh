#!/bin/bash
set -euo pipefail

die() {
  echo "❌ 错误: $*" >&2
  exit 1
}

run() {
  local desc="$1"
  shift
  set +e
  "$@"
  local rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    die "${desc} 失败（退出码: ${rc}）"
  fi
}

cd /workspace

run "git fetch origin" git fetch -q origin

stashed=0
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  run "暂存本地改动（stash）" git stash push -u -m "ci-temp"
  stashed=1
fi

if git ls-remote --exit-code --heads origin solo_main >/dev/null 2>&1; then
  run "检出 origin/solo_main" git fetch -q origin solo_main:refs/remotes/origin/solo_main
  run "切换到 solo_main" git checkout -B solo_main origin/solo_main
else
  run "从 origin/main 创建 solo_main" git checkout -B solo_main origin/main
  run "推送 solo_main 到远端" git push -q -u origin solo_main
fi

run "git pull --ff-only" git pull --ff-only -q origin solo_main

if [ "${stashed}" -eq 1 ]; then
  run "恢复本地改动（stash pop）" git stash pop --index
fi

run "安装 requirements.txt 依赖" python -m pip install --disable-pip-version-check -r requirements.txt
run "安装本项目（editable）" python -m pip install --disable-pip-version-check -e .

if ! command -v stock >/dev/null 2>&1; then
  die "stock 命令不可用（请检查 pip install -e . 是否成功、以及 PATH 是否包含 console_scripts）"
fi

mkdir -p output

if [ ! -f update_cache.sh ]; then
  die "未找到 update_cache.sh"
fi
run "执行 update_cache.sh" bash update_cache.sh

if [ ! -f my_daily_analysis.sh ]; then
  die "未找到 my_daily_analysis.sh"
fi
run "执行 my_daily_analysis.sh" bash my_daily_analysis.sh

while IFS= read -r f; do
  git add -f "$f"
done < <(find output -type f \( -name "*.xlsx" -o -name "*.png" \) -mmin -240)

if ! git diff --cached --quiet; then
  if ! git config user.email >/dev/null 2>&1; then
    git config user.email "ci@localhost"
  fi
  if ! git config user.name >/dev/null 2>&1; then
    git config user.name "ci-bot"
  fi
  run "git commit" git commit -m "chore: daily stock report $(date '+%Y-%m-%d')"
  run "git push" git push -q origin solo_main
fi
