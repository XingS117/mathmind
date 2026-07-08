<#
MathMind 生产启动脚本 (Windows PowerShell)

用法：
  powershell -File scripts\serve.ps1                # 默认监听 127.0.0.1:8000
  $env:MATHMIND_HOST="0.0.0.0"; powershell -File scripts\serve.ps1   # 允许局域网访问
  $env:MATHMIND_PORT="8080"; powershell -File scripts\serve.ps1     # 换端口

可选环境变量（LLM 也可从 SQLite 的 UserSettings 读取，env 优先）：
  MATHMIND_LLM_API_KEY   同 DEEPSEEK_API_KEY，任填其一
  MATHMIND_LLM_PROVIDER  默认 deepseek
  MATHMIND_LLM_MODEL     默认 deepseek-chat
  MATHMIND_LLM_BASE_URL  默认 https://api.deepseek.com/v1
  ADMIN_PASS             管理员初始密码（仅首次创建时生效）

启动后：
  - 前端： http://<host>:<port>/
  - API ： http://<host>:<port>/api/v1/...
  - 健康： http://<host>:<port>/health
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$host_ = $env:MATHMIND_HOST; if (-not $host_) { $host_ = "127.0.0.1" }
$port  = $env:MATHMIND_PORT; if (-not $port)  { $port  = "8000" }

$dist = Join-Path $root "frontend\dist\index.html"
if (-not (Test-Path $dist)) {
    Write-Warning "frontend/dist 不存在，前端将不会被 backend 托管。先运行： powershell -File scripts\build.ps1"
}

$py = (Get-Command python -ErrorAction SilentlyContinue) ?? (Get-Command py -ErrorAction SilentlyContinue)
if (-not $py) { throw "未找到 python" }

$env:PYTHONIOENCODING = "utf-8"
Write-Host "MathMind 启动中： http://${host_}:${port}/" -ForegroundColor Green
& $py.Source -m uvicorn backend.main:app --host $host_ --port $port