# MathMind 运营底座与账户安全实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让陌生学生能安全注册和使用 MathMind，同时让管理员能在不读取学习内容或完整 IP 的前提下处理账户和查看基础运行健康度。

**架构：** 在 SQLite 增加账户状态、登录事件、管理员审计事件和运行事件四类最小数据；认证路由负责注册/登录/资料修改，管理员路由仅返回汇总和脱敏数据。使用环境变量集中管理安全配置，所有业务路由继续通过现有 Bearer JWT 获取用户。

**技术栈：** FastAPI、SQLAlchemy、SQLite、PyJWT、Python `hashlib.scrypt`、React 19、TypeScript、Vite、PowerShell。

---

## 文件结构

- 创建：`backend/models/operations.py` — `LoginEvent`、`AdminAuditEvent`、`RuntimeEvent` ORM 模型。
- 创建：`backend/services/operations_service.py` — IP 脱敏/指纹、审计和运行事件写入。
- 创建：`backend/services/rate_limit_service.py` — 单进程、按类别和来源的滑动窗口限流。
- 创建：`backend/tests/test_auth_registration.py`、`backend/tests/test_operations_admin.py`。
- 创建：`scripts/backup.ps1`、`.env.example`、`frontend/src/pages/AccountPage.tsx`、`frontend/src/pages/AdminAccountsPage.tsx`。
- 修改：`backend/models/user.py`、`backend/database.py`、`backend/main.py`、认证/管理/上传路由、OCR/LLM 服务、前端 `App.tsx`、`LoginPage.tsx`、`SettingsPage.tsx`、`api.ts` 和部署文档。

## 任务 1：安全配置、数据模型和兼容迁移

**文件：** 创建 `backend/models/operations.py`；修改 `backend/models/user.py`、`backend/database.py`、`backend/services/auth_service.py`；测试 `backend/tests/test_auth_registration.py`。

- [ ] **步骤 1：编写失败测试**

```python
def test_legacy_password_is_accepted_then_marked_for_upgrade(self):
    encoded = legacy_hash("pw-123456")
    self.assertTrue(verify_password("pw-123456", encoded))
    self.assertTrue(needs_password_upgrade(encoded))
```

- [ ] **步骤 2：运行失败测试**

运行：`python -m unittest backend.tests.test_auth_registration.PasswordMigrationTest`

预期：FAIL，`legacy_hash` 与 `needs_password_upgrade` 尚不存在。

- [ ] **步骤 3：实现最小数据与密码安全代码**

在 `User` 增加 `is_active = Column(Boolean, default=True, nullable=False)` 与 `updated_at`；在 `init_db()` 导入新模型，并按既有 PRAGMA 模式为旧库补列。

```python
class LoginEvent(Base):
    __tablename__ = "login_events"
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True, index=True)
    occurred_at = Column(DateTime, server_default=func.now(), index=True)
    outcome = Column(String, nullable=False)
    ip_masked = Column(String, nullable=False)
    ip_fingerprint = Column(String, nullable=False, index=True)
    user_agent_family = Column(String, default="unknown")

class RuntimeEvent(Base):
    __tablename__ = "runtime_events"
    id = Column(String, primary_key=True)
    occurred_at = Column(DateTime, server_default=func.now(), index=True)
    feature = Column(String, nullable=False)
    engine_kind = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model_name = Column(String, default="")
    outcome = Column(String, nullable=False)
    duration_ms = Column(Integer, nullable=True)
    error_code = Column(String, nullable=True)
```

同步定义 `AdminAuditEvent(id, admin_user_id, target_user_id, action, occurred_at)`。模型不得含完整 IP、密码、API Key、题目或提示词字段。新密码格式为 `scrypt$<salt_hex>$<digest_hex>`；旧 SHA-256 格式只允许登录成功后升级：

```python
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + salt.hex() + "$" + digest.hex()

def needs_password_upgrade(encoded: str) -> bool:
    return bool(encoded) and not encoded.startswith("scrypt$")
```

- [ ] **步骤 4：运行通过测试并提交**

运行：`python -m unittest backend.tests.test_auth_registration.PasswordMigrationTest`

预期：PASS。

```bash
git add backend/models backend/database.py backend/services/auth_service.py backend/tests/test_auth_registration.py
git commit -m "feat(账户): 增加安全账户模型与密码迁移"
```

## 任务 2：公开注册、昵称修改与登录保护

**文件：** 创建 `backend/services/rate_limit_service.py`；修改 `backend/routers/auth.py`、`backend/services/operations_service.py`；测试 `backend/tests/test_auth_registration.py`。

- [ ] **步骤 1：编写失败 API 测试**

```python
def test_register_then_login_and_change_display_name(self):
    created = self.client.post("/api/v1/auth/register", json={"username": "new_user", "password": "pw-123456", "name": "小明"})
    self.assertEqual(created.status_code, 201)
    token = self.client.post("/api/v1/auth/login", json={"username": "new_user", "password": "pw-123456"}).json()["token"]
    updated = self.client.put("/api/v1/auth/profile", headers={"Authorization": f"Bearer {token}"}, json={"name": "小红"})
    self.assertEqual(updated.json()["name"], "小红")
```

追加：重复用户名 409；错误用户名和错误密码相同 401；停用账户 403；同一 IP 第六次失败登录 429。

- [ ] **步骤 2：运行失败测试**

运行：`python -m unittest backend.tests.test_auth_registration.AuthRegistrationApiTest`

预期：FAIL，`/auth/register` 与 `/auth/profile` 不存在。

- [ ] **步骤 3：实现端点、限流与事件**

```python
def allow(key: str, bucket: str, limit: int, window_seconds: int) -> bool: ...
def mask_ip(ip: str) -> str: ...
def fingerprint_ip(ip: str, secret: str) -> str:
    return hmac.new(secret.encode(), ip.encode(), hashlib.sha256).hexdigest()[:24]
```

新增 `POST /auth/register`（201）和 `PUT /auth/profile`。用户名要求 3–32 个字母、数字、下划线或连字符；显示姓名 1–32 字符；密码 8–128 字符。登录成功、失败、停用和限流均写 `LoginEvent`。客户端 IP 只从 `X-Forwarded-For` 第一项或 `request.client.host` 获得，落库前只能脱敏和指纹化。

- [ ] **步骤 4：运行验证并提交**

```powershell
python -m unittest backend.tests.test_auth_registration
python -m unittest discover -s backend/tests -p 'test_*.py'
```

预期：两条命令均为 `OK`。

```bash
git add backend/routers/auth.py backend/services/rate_limit_service.py backend/services/operations_service.py backend/tests/test_auth_registration.py
git commit -m "feat(账户): 支持公开注册、昵称修改与登录保护"
```

## 任务 3：管理员账户支持与匿名化运行事件

**文件：** 修改 `backend/routers/admin.py`、`backend/routers/upload.py`、`backend/services/ocr_service.py`、`backend/services/llm_service.py`；测试 `backend/tests/test_operations_admin.py`。

- [ ] **步骤 1：编写失败测试**

```python
def test_admin_can_disable_reset_and_view_masked_account_summary(self):
    response = self.admin.patch(f"/api/v1/admin/users/{self.student_id}/status", json={"is_active": False})
    self.assertEqual(response.status_code, 200)
    self.assertEqual(self.student_login().status_code, 403)
    overview = self.admin.get("/api/v1/admin/accounts-overview").json()
    self.assertIn("login_count", overview["users"][0])
    self.assertNotIn("203.0.113.42", str(overview))

def test_runtime_event_never_has_prompt_or_key(self):
    event = record_runtime_event(self.db, "llm", "model", "deepseek", "deepseek-chat", "success", 12)
    self.assertEqual(event.provider, "deepseek")
    self.assertFalse(hasattr(event, "prompt"))
```

还要断言：非管理员 403、管理员不能停用自己、重置和停用都会新增 `AdminAuditEvent`。

- [ ] **步骤 2：运行失败测试**

运行：`python -m unittest backend.tests.test_operations_admin`

预期：FAIL，管理端点和运行事件函数尚不存在。

- [ ] **步骤 3：实现最小管理 API**

新增 `PATCH /admin/users/{user_id}/status`、`POST /admin/users/{user_id}/reset-password`、`GET /admin/accounts-overview`、`GET /admin/runtime-overview`。账户概览只能返回：ID、用户名、显示姓名、状态、创建时间、登录次数、最近登录时间、最近脱敏 IP、设备概况。运行概览按 `feature/engine_kind/provider/model_name/outcome` 聚合计数和平均耗时。

```python
def record_runtime_event(db, feature, engine_kind, provider, model_name,
                         outcome, duration_ms, error_code=None): ...
```

在 OCR、视觉 OCR、文本模型调用的 `finally` 块记录耗时和固定错误码。严禁传入 `raw_text`、请求体、提示词、回答、配置对象或 API Key。

- [ ] **步骤 4：验证并提交**

```powershell
python -m unittest backend.tests.test_operations_admin
python -m unittest discover -s backend/tests -p 'test_*.py'
```

预期：均为 `OK`。

```bash
git add backend/routers/admin.py backend/routers/upload.py backend/services/ocr_service.py backend/services/llm_service.py backend/services/operations_service.py backend/tests/test_operations_admin.py
git commit -m "feat(管理): 增加账户审计与引擎健康概览"
```

## 任务 4：学生账户与管理员账户界面

**文件：** 创建 `frontend/src/pages/AccountPage.tsx`、`frontend/src/pages/AdminAccountsPage.tsx`；修改 `frontend/src/App.tsx`、`frontend/src/pages/LoginPage.tsx`、`frontend/src/services/api.ts`。

- [ ] **步骤 1：定义前端类型和 API**

```ts
export type AccountOverview = {
  id: string; username: string; name: string; is_active: boolean;
  login_count: number; last_login_at: string | null;
  last_ip_masked: string | null; user_agent_family: string | null;
};
export const register = (username: string, password: string, name: string) =>
  apiJson<{ token: string; user: AuthUser }>("/auth/register",
    { method: "POST", json: { username, password, name } });
export const updateProfile = (name: string) =>
  apiJson<AuthUser>("/auth/profile", { method: "PUT", json: { name } });
```

所有非 2xx 调用必须读出 `detail` 并在页面展示中文错误。

- [ ] **步骤 2：实现学生与管理员页面**

`LoginPage` 用 `mode: "login" | "register"` 切换表单；注册成功后直接调用 `onLogin(token)`。账户页只显示用户名（只读）、显示姓名编辑和改密码。仅 `user.role === "admin"` 时显示管理导航和管理员页；停用、启用和重置密码前使用 `window.confirm`。

- [ ] **步骤 3：运行前端验证和浏览器验收**

```powershell
cd frontend
npx tsc --noEmit
npm run build
node --test src/components/knowmapPicker.test.mjs
```

预期：退出码 0，Node 测试全部 PASS。

浏览器验收：在桌面和 390px 宽度下完成注册、昵称修改、登出/登录、管理员停用/恢复；控制台无错误；非管理员无法访问管理 API 或页面。

- [ ] **步骤 4：提交**

```bash
git add frontend/src/App.tsx frontend/src/pages/LoginPage.tsx frontend/src/pages/AccountPage.tsx frontend/src/pages/AdminAccountsPage.tsx frontend/src/services/api.ts
git commit -m "feat(前端): 增加注册、账户与管理员账户页"
```

## 任务 5：生产配置、每日备份和发布门禁

**文件：** 创建 `.env.example`、`scripts/backup.ps1`；修改 `backend/main.py`、`scripts/serve.ps1`、`docs/DEPLOYMENT.md`、`docs/DEPLOYMENT-live.md`；测试 `backend/tests/test_auth_registration.py`。

- [ ] **步骤 1：编写失败配置测试**

```python
def test_production_rejects_default_or_missing_secrets(self):
    with patched_env(MATHMIND_ENV="production", JWT_SECRET="", MATHMIND_IP_HASH_SECRET=""):
        with self.assertRaises(RuntimeError):
            load_runtime_config()
```

- [ ] **步骤 2：运行失败测试**

运行：`python -m unittest backend.tests.test_auth_registration.RuntimeConfigTest`

预期：FAIL，`load_runtime_config` 尚不存在。

- [ ] **步骤 3：实现配置和备份**

生产启动必须要求 `MATHMIND_ENV=production`、非默认 `JWT_SECRET`、`MATHMIND_IP_HASH_SECRET` 和非默认 `ADMIN_PASS`；日志不得打印管理员密码。开发环境才允许受控默认值，并记录警告。

`backup.ps1` 使用 Python sqlite3 `.backup` API 创建 `data/backups/mathmind-YYYYMMDD-HHMMSS.db` 和同名 `.sha256`，只保留最新 7 组，错误即退出非零，绝不删除源库。`.env.example` 只列变量名与说明，不放真实值。

- [ ] **步骤 4：执行恢复演练、完整测试并提交**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup.ps1
python -m unittest discover -s backend/tests -p 'test_*.py'
cd frontend; npx tsc --noEmit; npm run build; node --test src/components/knowmapPicker.test.mjs
```

预期：新备份与校验文件存在，所有命令退出码 0。复制新备份到临时文件并用 sqlite3 查询 `users` 表后删除临时文件，记录恢复演练输出。

```bash
git add .env.example backend/main.py scripts/backup.ps1 scripts/serve.ps1 docs/DEPLOYMENT.md docs/DEPLOYMENT-live.md backend/tests/test_auth_registration.py
git commit -m "chore(运维): 增加生产配置校验与数据库备份"
```

## 最终验收

- [ ] 新用户能注册、登录并修改显示姓名，用户名和历史数据保持不变。
- [ ] 停用账户无法登录；管理员能重置密码，所有管理动作可审计。
- [ ] 管理员只见脱敏网络信息和引擎元数据；响应不含完整 IP、密码、题目正文或 API Key。
- [ ] 生产环境拒绝开发默认密钥；备份可恢复到测试库。
- [ ] 后端完整测试、前端类型检查、构建、Node 测试和浏览器关键流程均通过。
