# 生产部署（腾讯云 Ubuntu）· mathmind.xingshuwen.com

已上线：**https://mathmind.xingshuwen.com/**

## 主机与账号

- 主机：腾讯云 CVM，IPv4 `111.229.187.91`（22 端口 SSH，密钥登录）
- SSH 用户：`ubuntu`
- SSH 私钥（本机不入库）：`C:\Users\shuwe\.ssh\mathmind_tencent.pem`
- 域名：`mathmind.xingshuwen.com`（A 记录 → `111.229.187.91`）
- 证书：Let’s Encrypt，`/etc/letsencrypt/live/mathmind.xingshuwen.com/`，`certbot` systemd timer 自动续签

## 服务器目录

```
/data/mathmind/
├── deploy.tar.gz          # 首次上传的完整代码 + 前端 dist
└── app/
    ├── backend/           # FastAPI 后端
    ├── frontend/dist/     # 前端产物（backend 直接 serve）
    ├── data/
    │   └── mathmind.db   # SQLite（首次启动 seed）
    ├── docs/
    ├── scripts/
    ├── tools/
    ├── requirements.txt
    ├── .venv/             # Python 3.12 venv
    └── .env               # 生产环境变量（chmod 600，未入库）
```

## systemd

- Unit：`/etc/systemd/system/mathmind.service`
- 启动命令：`.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8100`
- 常用运维：

```bash
sudo systemctl status mathmind
sudo systemctl restart mathmind
sudo journalctl -u mathmind -n 100 --no-pager
```

## nginx

- 站点：`/etc/nginx/sites-available/mathmind.xingshuwen.com`
- 80 → 301 到 443
- 443：`proxy_pass http://127.0.0.1:8100`，`client_max_body_size 30m`（覆盖多图上传）

## LLM 配置

`.env`（`/data/mathmind/app/.env`）由 systemd `EnvironmentFile=` 注入：

```
MATHMIND_LLM_API_KEY=sk-********
MATHMIND_LLM_PROVIDER=deepseek
MATHMIND_LLM_MODEL=deepseek-chat
MATHMIND_LLM_BASE_URL=https://api.deepseek.com/v1
```

还必须配置以下生产安全变量（使用不同的长随机字符串；`ADMIN_PASS` 不能是 `admin123`）：

```ini
MATHMIND_ENV=production
JWT_SECRET=replace-with-a-long-unique-secret
MATHMIND_IP_HASH_SECRET=replace-with-another-long-unique-secret
ADMIN_PASS=replace-with-a-strong-initial-admin-password
```

```bash
sudo chmod 600 /data/mathmind/app/.env
sudo systemctl restart mathmind
sudo journalctl -u mathmind -n 50 --no-pager
```

生产环境缺少这些安全变量或仍使用开发默认值时，服务会拒绝启动；日志不会打印管理员密码。

若既有管理员密码仍为 `admin123`，服务同样会拒绝启动，且普通启动绝不会自动修改既有密码。安全轮换时先停服务，编辑 `.env` 中的非默认 `ADMIN_PASS`，再在应用目录运行脚本；脚本不会输出密码：

```bash
sudo systemctl stop mathmind
cd /data/mathmind/app
./.venv/bin/python scripts/rotate_admin_password.py
sudo systemctl start mathmind
```

优先级：**env > SQLite UserSettings**，见 `backend/routers/upload.py:_get_llm_config`，测试 `backend/tests/test_llm_env_override.py`。

## 更新流程（源码变更后）

在开发机（Windows）：

```powershell
cd D:\Sven\maths\.worktrees\real-question-baseline
cd frontend
npm run build
cd ..
git archive --format=tar.gz -o _temp\src.tar.gz HEAD
# 打包时把 frontend/dist 补进去
if (Test-Path _temp\bundle) { Remove-Item _temp\bundle -Recurse -Force }
New-Item -ItemType Directory _temp\bundle | Out-Null
tar -xzf _temp\src.tar.gz -C _temp\bundle
Copy-Item frontend\dist _temp\bundle\frontend\ -Recurse -Force
Push-Location _temp\bundle
tar -czf ..\deploy-full.tar.gz .
Pop-Location
scp -i C:\Users\shuwe\.ssh\mathmind_tencent.pem _temp\deploy-full.tar.gz ubuntu@111.229.187.91:/data/mathmind/deploy.tar.gz
```

服务器：

```bash
cd /data/mathmind
sudo tar -xzf deploy.tar.gz -C app --no-same-owner --no-same-permissions
# SQLite 除了数据库文件外，还要在 data/ 创建 journal/WAL 文件；必须归服务用户所有。
sudo chown -R ubuntu:ubuntu /data/mathmind/app/data
sudo chmod 750 /data/mathmind/app/data
sudo chmod 640 /data/mathmind/app/data/mathmind.db
sudo systemctl restart mathmind
```

不要用 root 在 `data/` 中创建持久文件后直接上线；若目录属主变为 root，服务虽能启动，但注册、登录记录、错题保存等所有写入都会失败并报“readonly database”。

如 `requirements.txt` 有变动：`/data/mathmind/app/.venv/bin/pip install -r /data/mathmind/app/requirements.txt`。

## 数据库备份

```bash
cd /data/mathmind/app
pwsh -File scripts/backup.ps1
```

该脚本通过 Python SQLite 在线备份 API 创建 `data/backups/mathmind-时间戳.db` 与 SHA-256 校验文件，并保留最新 7 组。Ubuntu 上可用 cron 每天执行一次，例如：

```cron
# 先运行 command -v pwsh；将下方 /usr/bin/pwsh 替换为实际输出路径。
30 2 * * * cd /data/mathmind/app && /usr/bin/pwsh -File scripts/backup.ps1 >> /var/log/mathmind-backup.log 2>&1
```

若 `command -v pwsh` 没有输出，先按发行版的 PowerShell 安装说明安装 PowerShell，再创建该 cron 任务。备份脚本会优先使用 `/data/mathmind/app/.venv/bin/python`，无需依赖系统 Python 指向项目环境。

恢复前先停服务并保留故障库：`sudo systemctl stop mathmind`，将确认可读的备份复制到 `data/mathmind.db`，再执行 `sudo systemctl start mathmind`。演练检查示例：`python3 -c "import sqlite3; print(sqlite3.connect('data/backups/备份名.db').execute('select count(*) from users').fetchone())"`。

## 快速排障

- 500 ： `sudo journalctl -u mathmind -n 200`
- OCR 未 ready：默认 20-40s 初始化；从 `journalctl` 看 `PP-LCNet_x1_0_doc_ori` 下载进度
- 前端 404：确认 `frontend/dist/index.html` 存在，`backend/main.py` 启动日志有 `Serving frontend from ...`
