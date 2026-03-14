# Backend 运行与部署说明

本文档用于说明 AI 考试答题平台后端的本地运行、数据库迁移、接口验证和基础部署方式。

当前后端技术栈：

- Python 3.12+
- Poetry
- FastAPI
- SQLAlchemy 2
- Alembic
- SQLite（默认开发环境）

## 1. 目录说明

后端目录结构核心如下：

```text
backend/
├─ alembic/                # Alembic 迁移脚本
├─ app/
│  ├─ api/                 # 路由层
│  ├─ core/                # 配置、安全、响应结构
│  ├─ db/                  # 数据库连接与初始化
│  ├─ models/              # SQLAlchemy 模型
│  ├─ schemas/             # Pydantic 请求模型
│  └─ services/            # AI 任务、报告、学习计划、实时事件服务
├─ data/                   # 默认 SQLite 数据目录
├─ alembic.ini             # Alembic 配置文件
├─ pyproject.toml          # Poetry 依赖配置
└─ README.md
```

## 2. 环境要求

在开始运行前，请确认本机具备以下环境：

- Python 3.12 或更高版本
- Poetry 2.x
- PowerShell、Windows Terminal 或其他命令行工具

建议先检查版本：

```powershell
python --version
poetry --version
```

如果 Poetry 尚未安装，可参考官方方式安装：

```powershell
pip install poetry
```

如果你使用 conda，也可以先激活自己的 Python 3.12 环境，再继续后面的步骤。

## 3. 进入后端目录

在项目根目录执行：

```powershell
cd backend
```

后续所有命令默认都在 backend 目录执行。

## 4. 绑定正确的 Python 解释器

本项目要求 Python 3.12。如果你的机器上有多个 Python 版本，建议先让 Poetry 显式绑定到正确解释器。

先查看当前可用 Python：

```powershell
python --version
```

如果当前就是 3.12，可直接执行：

```powershell
poetry env use python
```

如果你要指定某个解释器路径，例如 conda 环境中的 Python：

```powershell
poetry env use D:/Software/anaconda3/envs/answer/python.exe
```

绑定成功后，可检查 Poetry 虚拟环境路径：

```powershell
poetry env info --path
```

## 5. 安装依赖

执行以下命令安装项目依赖：

```powershell
poetry install --no-root
```

说明：

- `--no-root` 表示只安装依赖，不把当前项目作为发布包安装。
- 如果你只是开发和运行服务，这样已经足够。

安装完成后，建议验证关键依赖是否在 Poetry 环境中可用：

```powershell
poetry run python -c "import fastapi, sqlalchemy, jose, alembic; print('dependencies ok')"
```

## 6. 运行时配置

后端运行时配置现在主要通过 `.env` 文件和进程环境变量加载。

默认配置文件：

- `.env.dev`
- `.env.prod`
- `app/core/config.py`

建议的使用方式：

1. 开发环境默认读取 `backend/.env.dev`
1. 生产环境可设置 `APP_ENV=prod`，项目会读取 `backend/.env.prod`
1. 如果需要，也可以直接注入系统环境变量覆盖文件中的值

加载优先级如下，越靠前优先级越高：

1. 进程环境变量
1. 当前环境对应的 `.env` 文件
1. `app/core/config.py` 中的默认值

### 6.1 .env 示例

开发环境默认读取 `backend/.env.dev`，内容例如：

```env
PROJECT_NAME=AI考试答题平台后端-开发环境
API_V1_PREFIX=/api/v1
SECRET_KEY=dev-secret-key-change-me
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./data/app.dev.db
OPENAI_API_KEY=
DEBUG=true
```

说明：

- 环境变量中的值会覆盖当前环境对应的 `.env` 文件
- 生产环境必须替换 `SECRET_KEY`
- 如果接 PostgreSQL 或 MySQL，请修改 `DATABASE_URL`

### 6.2 生产环境配置

如果设置 `APP_ENV=prod`，项目会改为读取 `backend/.env.prod`。

## 7. 初始化数据库迁移

本项目已经从“启动时自动建表”切换到 Alembic 迁移管理。

首次运行前，请先执行数据库迁移：

```powershell
poetry run alembic upgrade head
```

作用：

- 创建 Alembic 管理表
- 应用初始数据库结构
- 建立用户、班级、题目、考试、作答、AI 任务、报告等核心表

如果迁移成功，数据库文件会出现在：

```text
backend/data/app.db
```

## 8. 使用脚本进行部署与运行

为减少手工输入命令，项目提供了 `backend/scripts` 下的脚本：

- `deploy.ps1` / `deploy.sh`：执行部署准备，包括依赖安装、数据库迁移、健康检查。
- `run.ps1` / `run.sh`：启动后端服务，支持开发模式和生产模式。

### 8.1 Windows PowerShell

在 `backend` 目录下执行：

```powershell
./scripts/deploy.ps1
./scripts/run.ps1 -Mode dev
```

常见参数：

- `-PythonExecutable D:/Software/anaconda3/envs/answer/python.exe`：显式绑定 Poetry 的 Python。
- `-SkipInstall`：跳过 `poetry install --no-root`。
- `-SkipMigrate`：跳过 Alembic 迁移。
- `-SkipHealthCheck`：跳过部署阶段健康检查。
- `-PythonExecutable D:/Software/anaconda3/envs/answer/python.exe`：在运行脚本中显式绑定 Poetry 的 Python。
- `-ListenHost 0.0.0.0 -Port 8000`：指定监听地址和端口。
- `-Mode prod -Workers 2`：以生产模式启动，并指定 worker 数量。

### 8.2 Bash

在 `backend` 目录下执行：

```bash
./scripts/deploy.sh
./scripts/run.sh --mode dev
```

常见参数：

- `--python /path/to/python`：显式绑定 Poetry 的 Python。
- `--skip-install`：跳过 `poetry install --no-root`。
- `--skip-migrate`：跳过 Alembic 迁移。
- `--skip-health-check`：跳过部署阶段健康检查。
- `--python /path/to/python`：在运行脚本中显式绑定 Poetry 的 Python。
- `--host 0.0.0.0 --port 8000`：指定监听地址和端口。
- `--mode prod --workers 2`：以生产模式启动，并指定 worker 数量。

## 9. 启动后端服务

推荐启动命令：

```powershell
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

参数说明：

- `app.main:app`：FastAPI 应用入口
- `--host 127.0.0.1`：仅本机访问
- `--port 8000`：监听端口 8000
- `--reload`：开发模式下文件变化自动重启

如果你要局域网访问，可改成：

```powershell
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

如果 8000 端口已被占用，可换成 8001：

```powershell
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

## 10. 启动成功后的访问地址

启动成功后，可访问：

- 健康检查：`http://127.0.0.1:8000/health`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`
- ReDoc 文档：`http://127.0.0.1:8000/redoc`

如果你改了端口，请把 `8000` 替换成实际端口。

## 11. 验证服务是否正常

### 11.1 浏览器验证

直接打开：

```text
http://127.0.0.1:8000/health
```

预期返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "ok"
  },
  "request_id": "req_xxxxxx",
  "timestamp": "2026-03-13T00:00:00+00:00"
}
```

### 11.2 命令行验证

使用 curl：

```powershell
curl http://127.0.0.1:8000/health
```

或使用 Poetry 环境直接验证：

```powershell
poetry run python -c "from fastapi.testclient import TestClient; from app.main import app; client = TestClient(app); print(client.get('/health').json())"
```

## 12. 推荐的本地启动顺序

每次新机器或新环境上运行，建议严格按以下顺序：

1. 进入后端目录

```powershell
cd backend
```

1. 绑定 Python 3.12 解释器

```powershell
poetry env use python
```

1. 安装依赖

```powershell
poetry install --no-root
```

1. 执行数据库迁移

```powershell
poetry run alembic upgrade head
```

1. 启动服务

```powershell
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 12. 常用开发命令

### 12.1 查看 Poetry 虚拟环境路径

```powershell
poetry env info --path
```

### 12.2 查看已安装依赖

```powershell
poetry show
```

### 12.3 新增依赖

```powershell
poetry add package-name
```

例如新增 Redis：

```powershell
poetry add redis
```

### 12.4 生成新迁移

当你修改了模型结构后，执行：

```powershell
poetry run alembic revision --autogenerate -m "describe your change"
```

然后再应用迁移：

```powershell
poetry run alembic upgrade head
```

### 12.5 回滚一步迁移

```powershell
poetry run alembic downgrade -1
```

## 13. 已实现的最小联调链路

当前已经可以完成以下核心流程：

1. 教师注册与登录
2. 教师创建班级
3. 教师创建题目
4. 教师创建并发布考试
5. 学生通过班级邀请码注册
6. 学生开始考试并保存答案
7. 学生提交考试
8. 系统生成 AI 分析任务与学习计划任务
9. 教师或学生查询 AI 任务状态
10. 生成报告并通过 WebSocket 接收任务进度事件

## 14. WebSocket 调试方式

当前已支持的实时接口包括：

- `/ws/exams/{exam_id}/submissions/{submission_id}`
- `/ws/ai-tasks`

例如订阅 AI 任务进度：

1. 先通过 HTTP 接口生成一个任务，例如报告生成任务
1. 连接 WebSocket：

```text
ws://127.0.0.1:8000/ws/ai-tasks
```

1. 发送订阅消息：

```json
{
  "task_ids": ["task_xxx"]
}
```

1. 服务端会推送：

```json
{
  "id": "evt_xxx",
  "seq": 1,
  "event": "task_progress",
  "data": {
    "task_id": "task_xxx",
    "status": "pending",
    "progress": 0
  },
  "timestamp": "2026-03-13T00:00:00+00:00"
}
```

## 15. 常见问题

### 15.1 `ModuleNotFoundError: No module named 'jose'`

原因：

- 你使用了系统 Python 启动，而不是 Poetry 虚拟环境。

正确方式：

```powershell
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

不要直接执行：

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 15.2 `Poetry could not find a pyproject.toml file`

原因：

- 你不在 backend 目录下执行 Poetry 命令。

解决方式：

```powershell
cd backend
poetry install --no-root
```

### 15.3 8000 端口被占用

报错特征：

- `WinError 10048`

解决方式：

```powershell
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### 15.4 编辑器提示 `jose` 或 `passlib` 无法解析

原因：

- VS Code 当前选中的 Python 解释器不是 Poetry 虚拟环境。

解决方式：

1. 查看虚拟环境路径：

```powershell
poetry env info --path
```

1. 在 VS Code 中切换解释器到该环境下的 Python。

### 15.5 Windows 下 bcrypt 兼容问题

当前项目已切换到 `pbkdf2_sha256` 作为密码哈希方案，避免 `passlib + bcrypt` 在部分 Windows + Python 3.12 环境下出现兼容问题。

## 16. 基础部署建议

如果你要部署到测试环境或服务器，建议最少执行以下流程：

1. 安装 Python 3.12 与 Poetry
2. 拉取代码
3. 进入 backend 目录
4. 执行 `poetry install --no-root`
5. 配置 `.env`
6. 执行 `poetry run alembic upgrade head`
7. 使用 Uvicorn 或 Gunicorn + Uvicorn Worker 启动服务

开发环境启动示例：

```powershell
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

如果后续切换到 PostgreSQL、Redis、真实任务队列和独立 AI Worker，建议再补充：

- 反向代理，例如 Nginx
- 进程托管，例如 systemd、Supervisor、PM2 或 NSSM
- 独立日志与监控
- HTTPS 与跨域安全配置

## 17. 一条命令回顾

如果你已经装好 Python 和 Poetry，最常用的完整启动流程就是：

```powershell
cd backend
poetry install --no-root
poetry run alembic upgrade head
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

执行完后访问：

```text
http://127.0.0.1:8000/docs
```

即可开始调试接口。
