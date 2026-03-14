param(
    [ValidateSet("dev", "prod")]
    [string]$Mode = "dev",
    [string]$PythonExecutable = "",
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 8000,
    [int]$Workers = 1,
    [switch]$SkipMigrate
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Resolve-Path (Join-Path $scriptDir "..")

function Assert-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "未找到命令: $Name"
    }
}

Set-Location $backendDir
Assert-Command -Name "poetry"

if ($PythonExecutable) {
    Write-Host "==> 绑定 Poetry Python 解释器" -ForegroundColor Cyan
    poetry env use $PythonExecutable
}

if (-not $SkipMigrate) {
    Write-Host "==> 执行数据库迁移" -ForegroundColor Cyan
    poetry run alembic upgrade head
}

if ($Mode -eq "dev") {
    Write-Host "==> 启动开发模式服务" -ForegroundColor Cyan
    poetry run uvicorn app.main:app --host $ListenHost --port $Port --reload
}
else {
    if ($Workers -lt 1) {
        throw "Workers 必须大于等于 1"
    }

    Write-Host "==> 启动生产模式服务" -ForegroundColor Cyan
    poetry run uvicorn app.main:app --host $ListenHost --port $Port --workers $Workers
}