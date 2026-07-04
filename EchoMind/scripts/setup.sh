#!/bin/bash
# EchoMind 部署构建脚本 - 安装依赖并准备运行环境

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

echo "[setup] Installing Python dependencies from requirements.txt..."

# 使用 pip 安装依赖（项目使用 requirements.txt）
pip install --upgrade pip
pip install -r requirements.txt

echo "[setup] Dependencies installed successfully."
