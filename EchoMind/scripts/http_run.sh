#!/bin/bash
# EchoMind 部署运行脚本 - 启动 FastAPI HTTP 服务

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

PORT=5000

usage() {
  echo "Usage: $0 -p <port>"
}

while getopts "p:h" opt; do
  case "$opt" in
    p)
      PORT="$OPTARG"
      ;;
    h)
      usage
      exit 0
      ;;
    \?)
      echo "Invalid option: -$OPTARG"
      usage
      exit 1
      ;;
  esac
done

echo "[run] Starting EchoMind FastAPI server on port $PORT..."

# 加载环境变量
if [ -f ".env" ]; then
  set -a
  source .env
  set +a
fi

# 启动 FastAPI 应用
exec python -m uvicorn api.main:app --host 0.0.0.0 --port "$PORT"
