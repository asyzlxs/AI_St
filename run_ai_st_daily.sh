#!/usr/bin/env bash
set -u

WORKDIR="/workspace/AI_St"
REPO_URL="https://github.com/asyzlxs/AI_St.git"

timestamp() {
  date +"%Y-%m-%d_%H-%M-%S"
}

log() {
  echo "[$(date +"%F %T")] $*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

is_git_clean() {
  # 0 = clean, 1 = dirty
  git diff --quiet || return 1
  git diff --cached --quiet || return 1
  # 允许 logs/ 与 output/ 产生未跟踪文件，不影响“干净工作区”判定
  local porcelain
  porcelain="$(git status --porcelain | grep -Ev '^\?\? (logs/|output/)' || true)"
  [[ -z "${porcelain}" ]] || return 1
  return 0
}

main() {
  local ts log_dir log_file
  ts="$(timestamp)"

  if [[ ! -d "$WORKDIR" ]]; then
    mkdir -p "$(dirname "$WORKDIR")"
    log "Workdir not found, cloning: $REPO_URL -> $WORKDIR"
    git clone "$REPO_URL" "$WORKDIR" || fail "git clone 失败"
  fi

  if [[ ! -d "$WORKDIR/.git" ]]; then
    fail "$WORKDIR 存在但不是 Git 仓库（缺少 .git）"
  fi

  cd "$WORKDIR" || fail "无法进入目录：$WORKDIR"

  # 初始化日志（在进入仓库后，确保写入到项目 logs 目录）
  log_dir="$WORKDIR/logs"
  mkdir -p "$log_dir"
  log_file="$log_dir/run_${ts}.log"

  # 将后续所有输出同时写到控制台和日志
  exec > >(tee -a "$log_file") 2>&1
  log "===== AI_St daily run start ====="
  log "WORKDIR=$WORKDIR"
  log "LOGFILE=$log_file"

  # 如果工作区干净则拉取；如果有本地修改则保留并继续运行
  if is_git_clean; then
    log "Git workspace clean, pulling latest (ff-only)..."
    git pull --ff-only || fail "git pull 失败（可能需要手工处理分支/冲突）"
  else
    log "Git workspace NOT clean, keep local changes and continue (skip pull)."
    git status --porcelain || true
  fi

  # 运行前确认关键脚本存在（使用当前本地版本）
  local required
  for required in ensure_env.sh update_cache.sh my_daily_analysis.sh; do
    [[ -f "$WORKDIR/$required" ]] || fail "缺少必需文件：$WORKDIR/$required"
  done

  mkdir -p "$WORKDIR/output"

  log "----- Step 1/2: update_cache.sh -----"
  if ! bash "$WORKDIR/update_cache.sh"; then
    fail "update_cache.sh 执行失败，已停止；请查看上述错误原因。"
  fi
  log "update_cache.sh 成功"

  log "----- Step 2/2: my_daily_analysis.sh -----"
  if ! bash "$WORKDIR/my_daily_analysis.sh"; then
    fail "my_daily_analysis.sh 执行失败；错误已写入日志。"
  fi
  log "my_daily_analysis.sh 成功"

  log "===== AI_St daily run done ====="
}

main "$@"

