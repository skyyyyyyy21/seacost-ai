#!/usr/bin/env bash
set -euo pipefail

# 基于脚本位置定位项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# 显式声明关键环境变量
export PORT=5000
export API_PORT=5000

# 清理 5000 端口残留进程（绝不碰 9000）
fuser -k 5000/tcp 2>/dev/null || true
sleep 1

echo "[SeaCost AI] 启动预览服务..."
echo "[SeaCost AI] 访问地址: http://0.0.0.0:5000"

# 启动 FastAPI 服务
exec uvicorn api.main:app --host 0.0.0.0 --port 5000
