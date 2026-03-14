#!/usr/bin/env bash

set -euo pipefail

PYTHON_EXECUTABLE=""
SKIP_INSTALL=false
SKIP_MIGRATE=false
SKIP_HEALTH_CHECK=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --python)
            PYTHON_EXECUTABLE="$2"
            shift 2
            ;;
        --skip-install)
            SKIP_INSTALL=true
            shift
            ;;
        --skip-migrate)
            SKIP_MIGRATE=true
            shift
            ;;
        --skip-health-check)
            SKIP_HEALTH_CHECK=true
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

step() {
    echo "==> $1"
}

assert_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "未找到命令: $1" >&2
        exit 1
    fi
}

cd "$BACKEND_DIR"
assert_command poetry

if [[ -n "$PYTHON_EXECUTABLE" ]]; then
    step "绑定 Poetry Python 解释器"
    poetry env use "$PYTHON_EXECUTABLE"
fi

if [[ "$SKIP_INSTALL" != true ]]; then
    step "安装后端依赖"
    poetry install --no-root
fi

if [[ "$SKIP_MIGRATE" != true ]]; then
    step "执行数据库迁移"
    poetry run alembic upgrade head
fi

if [[ "$SKIP_HEALTH_CHECK" != true ]]; then
    step "执行应用健康检查"
    poetry run python -c 'from fastapi.testclient import TestClient; from app.main import app; client = TestClient(app); response = client.get("/health"); response.raise_for_status(); print(response.json())'
fi

echo "部署准备完成。"