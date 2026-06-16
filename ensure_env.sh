#!/usr/bin/env bash
# ============================================================
#  Python 虚拟环境保障脚本
#  - 自动创建并复用项目内 .venv
#  - 自动安装 requirements.txt 与本项目（提供 stock 命令）
#  用法:
#    source ./ensure_env.sh
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
REQ_FILE="${PROJECT_DIR}/requirements.txt"
HASH_FILE="${VENV_DIR}/.deps_hash"

if ! command -v python3 >/dev/null 2>&1; then
  echo "错误: 未找到 python3，请先安装 Python 3" >&2
  exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install -U pip setuptools wheel >/dev/null

deps_hash=""
if [[ -f "${REQ_FILE}" ]]; then
  deps_hash="$(sha256sum "${REQ_FILE}" "${PROJECT_DIR}/setup.py" 2>/dev/null | sha256sum | awk '{print $1}')"
else
  deps_hash="$(sha256sum "${PROJECT_DIR}/setup.py" 2>/dev/null | awk '{print $1}')"
fi

if [[ ! -f "${HASH_FILE}" ]] || [[ "$(cat "${HASH_FILE}")" != "${deps_hash}" ]]; then
  echo "[ensure_env] Installing dependencies into ${VENV_DIR} ..."
  if [[ -f "${REQ_FILE}" ]]; then
    python -m pip install -r "${REQ_FILE}"
  fi
  # 安装本项目以提供 `stock` 命令
  python -m pip install -e "${PROJECT_DIR}"
  echo "${deps_hash}" > "${HASH_FILE}"
else
  echo "[ensure_env] Dependencies already satisfied (hash match)."
fi


