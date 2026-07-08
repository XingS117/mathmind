<#
MathMind 一键构建脚本 (Windows PowerShell)

用法：
  powershell -File scripts\build.ps1

会做的事：
  1. 检查 Python 3.10+ / Node 18+ 是否可用
  2. 安装/校验后端 Python 依赖
  3. 安装前端 npm 依赖并构建 frontend/dist
  4. 完成后提示用运行 scripts\serve.ps1 启动生产版
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== [1/4] 检查运行时 ===" -ForegroundColor Cyan
$py = (Get-Command python -ErrorAction SilentlyContinue) `
      ?? (Get-Command py -ErrorAction SilentlyContinue)
if (-not $py) { throw "未找到 python，请先安装 Python 3.10+ 并加入 PATH" }
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { throw "未找到 node，请先安装 Node.js 18+ 并加入 PATH" }
$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) { throw "未找到 npm" }
Write-Host "python: $($py.Source)"
Write-Host "node:   $($node.Source)"

Write-Host "=== [2/4] 检查后端依赖 ===" -ForegroundColor Cyan
& $py.Source -c "import fastapi, uvicorn, sqlalchemy, paddleocr; print('backend deps OK')"
if ($LASTEXITCODE -ne 0) {
    throw "缺少 Python 依赖，请先安装：pip install fastapi uvicorn sqlalchemy paddleocr httpx python-multipart"
}

Write-Host "=== [3/4] 构建前端 ===" -ForegroundColor Cyan
Push-Location frontend
try {
    if (-not (Test-Path node_modules)) {
        Write-Host "首次运行，安装 npm 依赖..."
        & npm.cmd install
        if ($LASTEXITCODE -ne 0) { throw "npm install 失败" }
    }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build 失败" }
} finally {
    Pop-Location
}

Write-Host "=== [4/4] 构建完成 ===" -ForegroundColor Green
Write-Host "前端产物: frontend/dist"
Write-Host "下一步：powershell -File scripts\serve.ps1"