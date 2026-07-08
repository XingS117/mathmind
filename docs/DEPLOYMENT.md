# MathMind 单机部署（Windows）

本项目上线默认按"家用单机 + 单端口"模式部署：backend 直接托管 `frontend/dist`，用户只需访问一个地址，即可用完整功能。

## 一键流程

```powershell
# 1. 构建（安装 npm 依赖 + vite build，产出 frontend/dist）
powershell -ExecutionPolicy Bypass -File scripts\build.ps1

# 2. 启动生产服务（默认监听 127.0.0.1:8000）
powershell -ExecutionPolicy Bypass -File scripts\serve.ps1

# 打开浏览器： http://127.0.0.1:8000/
```

**只在本机使用**：默认 `127.0.0.1:8000`，从其他设备访问不到；这是安全默认值。

## 让家里其他设备访问（同一 Wi-Fi）

```powershell
$env:MATHMIND_HOST="0.0.0.0"
$env:MATHMIND_PORT="8000"   # 可省，默认 8000
powershell -ExecutionPolicy Bypass -File scripts\serve.ps1
```

启动后：
- 在本机查一下 IP：`ipconfig`（找 "无线局域网适配器 WLAN" 的 IPv4，如 `192.168.0.106`）
- 手机/平板/其他电脑打开：`http://192.168.0.106:8000/`
- 若打不开：Windows 防火墙首次会弹窗，允许 python.exe 通信即可。

## LLM API Key 配置

优先级：**环境变量 > SQLite UserSettings 表**。生产建议用 env，key 不再存进 DB。

```powershell
$env:MATHMIND_LLM_API_KEY   = "sk-xxxxxxxxxxxx"        # 必填
$env:MATHMIND_LLM_PROVIDER  = "deepseek"               # 可选，默认 deepseek
$env:MATHMIND_LLM_MODEL     = "deepseek-chat"          # 可选，默认 deepseek-chat
$env:MATHMIND_LLM_BASE_URL  = "https://api.deepseek.com/v1"   # 可选
powershell -ExecutionPolicy Bypass -File scripts\serve.ps1
```

兼容别名：`DEEPSEEK_API_KEY` 同样有效（同 `MATHMIND_LLM_API_KEY`）。

若不设置 env，backend 会回退到读 SQLite `UserSettings` 表（也就是"设置页"配的 key），旧的部署方式仍然可用。

## 开机自启（Windows 计划任务）

```powershell
# 用管理员 PowerShell 执行一次即可：
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
           -Argument "-NoProfile -ExecutionPolicy Bypass -File D:\Sven\maths\.worktrees\real-question-baseline\scripts\serve.ps1" `
           -WorkingDirectory "D:\Sven\maths\.worktrees\real-question-baseline"
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "MathMind" -Action $action -Trigger $trigger -RunLevel Highest
```

停用：`Unregister-ScheduledTask -TaskName MathMind -Confirm:$false`。

## 数据库

- 位置：`mathmind.db`（SQLite，工作树根目录）
- 备份：直接复制这个文件即可。
- 出问题时：删除后重启会自动 seed（会丢历史）；建议先备份。
- 目前 `mathmind.db` 已含若干开发测试题与复习记录；如需干净上线：备份后 `Remove-Item mathmind.db`，重启 backend。

## 端口 / 反代 / HTTPS（可选）

家用单端口方案不需要 nginx。若要挂公网 + HTTPS：
- 用 Caddy 或 nginx 反代到 `127.0.0.1:8000`
- Caddy 一行配置：`your-domain.com { reverse_proxy 127.0.0.1:8000 }`

## 卸载/停止

- 前台窗口：Ctrl+C
- 后台计划任务：`Unregister-ScheduledTask -TaskName MathMind`
- 端口占用查看：`Get-NetTCPConnection -State Listen | ? LocalPort -eq 8000`