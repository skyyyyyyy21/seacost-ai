#!/usr/bin/env bash
set -euo pipefail

# 基于脚本位置定位项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "[SeaCost AI] 安装依赖..."

# 使用 pip 安装依赖
pip install -q -r requirements.txt

echo "[SeaCost AI] 依赖安装完成"
