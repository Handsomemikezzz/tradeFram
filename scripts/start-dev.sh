#!/usr/bin/env bash
# 启动 FastAPI (:8000) + Vite (:3000)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"

require_dir() {
  [[ -d "$1" ]] || { echo "$2"; exit 1; }
}

require_dir .venv "未找到 .venv：python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
require_dir node_modules "未找到 node_modules：npm install"

[[ ! -f .env && -f .env.example ]] && cp .env.example .env

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ "${AKSHARE_BYPASS_PROXY:-true}" == "true" ]]; then
  AKSHARE_NO_PROXY_DEFAULT="localhost,127.0.0.1,::1,push2.eastmoney.com,push2his.eastmoney.com,emappdata.eastmoney.com,*.eastmoney.com,eastmoney.com,qt.gtimg.cn,finance.pae.baidu.com,finance.sina.com.cn,*.sina.com.cn,proxy.finance.qq.com,*.qq.com"
  export NO_PROXY="${NO_PROXY:+$NO_PROXY,}$AKSHARE_NO_PROXY_DEFAULT"
  export no_proxy="${no_proxy:+$no_proxy,}$AKSHARE_NO_PROXY_DEFAULT"
fi

BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  for pid in "$FRONTEND_PID" "$BACKEND_PID"; do
    [[ -n "$pid" ]] || continue
    kill -0 "$pid" 2>/dev/null || continue
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

VENV_BIN="${ROOT}/.venv/bin"
PYTHON_BIN="${PYTHON_BIN:-$VENV_BIN/python3}"

echo "启动后端 http://127.0.0.1:${BACKEND_PORT}"
if ! "$PYTHON_BIN" -c "import uvicorn" >/dev/null 2>&1; then
  echo "错误：当前虚拟环境未安装 uvicorn。请先执行：$VENV_BIN/pip install -r requirements.txt"
  exit 1
fi
"$PYTHON_BIN" -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port "$BACKEND_PORT" &
BACKEND_PID=$!

echo "等待 /health"
for _ in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null; then
    echo "后端就绪。"
    break
  fi
  sleep 0.25
done

if ! curl -sf "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null; then
  echo "错误：后端未在预期时间内响应 /health，请查看上方 uvicorn 日志。"
  exit 1
fi

echo "启动前端 http://127.0.0.1:3000"
npm run dev &
FRONTEND_PID=$!
wait "$FRONTEND_PID"
