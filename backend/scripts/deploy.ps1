param(
    [string]$PythonExecutable = "",
    [switch]$SkipInstall,
    [switch]$SkipMigrate,
    [switch]$SkipHealthCheck
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Resolve-Path (Join-Path $scriptDir "..")

function Invoke-Step {
    param(
        [string]$Message,
        [scriptblock]$Action
    )

    Write-Host "==> $Message" -ForegroundColor Cyan
    & $Action
}

function Assert-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "未找到命令: $Name"
    }
}

Set-Location $backendDir
Assert-Command -Name "poetry"

if ($PythonExecutable) {
    Invoke-Step -Message "绑定 Poetry Python 解释器" -Action {
        poetry env use $PythonExecutable
    }
}

if (-not $SkipInstall) {
    Invoke-Step -Message "安装后端依赖" -Action {
        poetry install --no-root
    }
}

if (-not $SkipMigrate) {
    Invoke-Step -Message "执行数据库迁移" -Action {
        poetry run alembic upgrade head
    }
}

if (-not $SkipHealthCheck) {
    Invoke-Step -Message "执行应用健康检查" -Action {
        poetry run python -c 'from fastapi.testclient import TestClient; from app.main import app; client = TestClient(app); response = client.get("/health"); response.raise_for_status(); print(response.json())'
    }
}

Write-Host "部署准备完成。" -ForegroundColor Green