#!/usr/bin/env bash

set -euo pipefail

MODE="dev"
PYTHON_EXECUTABLE=""
HOST="127.0.0.1"
PORT="8000"
WORKERS="1"
SKIP_MIGRATE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --python)
            PYTHON_EXECUTABLE="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --skip-migrate)
            SKIP_MIGRATE=true
            shift
            ;;
        *)
            echo "未知参数: $1" >&2
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

assert_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "未找到命令: $1" >&2
        exit 1
    fi
}

cd "$BACKEND_DIR"
assert_command poetry

if [[ -n "$PYTHON_EXECUTABLE" ]]; then
    echo "==> 绑定 Poetry Python 解释器"
    poetry env use "$PYTHON_EXECUTABLE"
fi

if [[ "$SKIP_MIGRATE" != true ]]; then
    echo "==> 执行数据库迁移"
    poetry run alembic upgrade head
fi

if [[ "$MODE" == "dev" ]]; then
    echo "==> 启动开发模式服务"
    poetry run uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
elif [[ "$MODE" == "prod" ]]; then
    if [[ "$WORKERS" -lt 1 ]]; then
        echo "workers 必须大于等于 1" >&2
        exit 1
    fi

    echo "==> 启动生产模式服务"
    poetry run uvicorn app.main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
else
    echo "mode 只支持 dev 或 prod" >&2
    exit 1
fi