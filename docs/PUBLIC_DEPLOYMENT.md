# MathMind 公共部署说明

本文档只说明通用安全要求。请根据自己的运行环境配置域名、反向代理和访问控制。

## 环境变量

从模板创建本地环境文件：

```powershell
Copy-Item .env.example .env
```

生产环境必须设置：

```text
MATHMIND_ENV=production
JWT_SECRET=<long-random-secret>
MATHMIND_IP_HASH_SECRET=<different-long-random-secret>
ADMIN_PASS=<strong-initial-admin-password>
```

三个秘密必须不同且足够长。`.env` 只能保存在部署环境中，不能提交到 Git 或通过客户端发送。

模型 API Key 使用 `MATHMIND_LLM_API_KEY` 等环境变量配置。为每个环境使用独立凭据，并定期轮换。

## 运行方式

先构建前端，再以单个后端进程提供 API 和前端静态资源：

```powershell
Set-Location frontend
npm install
npm run build

Set-Location ..
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

将应用置于受控的 HTTPS 反向代理之后，并仅开放实际需要的端口。数据库、备份和日志应保存到受访问控制的存储位置，定期验证备份能够恢复。
