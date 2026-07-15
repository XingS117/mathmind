# 注册用户名即时可用性实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 恢复生产注册写入，并让学生在注册输入用户名时即时获得可用性结果。

**架构：** 后端增加受限流保护的只读用户名可用性接口，沿用注册格式规则和现有数据库查询。前端对有效用户名作 400ms 防抖请求，使用状态机控制提示和按钮；最终注册仍由后端的 409 冲突校验兜底。

**技术栈：** FastAPI、SQLAlchemy、React、TypeScript、Vitest、Python unittest。

---

### 任务 1：后端用户名可用性接口

**文件：**
- 修改：`backend/routers/auth.py:27-82`
- 修改：`backend/tests/test_auth_registration.py:121-160`

- [x] **步骤 1：编写失败的接口测试**

在 `PublicAuthFlowTest` 增加：

```python
def test_username_availability_reports_available_and_taken(self):
    self.assertEqual(self.client.get("/api/v1/auth/username-availability", params={"username": "freeuser"}).json(), {"available": True})
    self.assertEqual(self.register(username="takenuser").status_code, 201)
    self.assertEqual(self.client.get("/api/v1/auth/username-availability", params={"username": "takenuser"}).json(), {"available": False})

def test_username_availability_reuses_registration_format_rule(self):
    response = self.client.get("/api/v1/auth/username-availability", params={"username": "中文用户"})
    self.assertEqual(response.status_code, 422)
    self.assertTrue(response.json()["detail"][0]["msg"].endswith("用户名仅支持 3–32 位英文字母或数字"))
```

- [x] **步骤 2：运行测试验证失败**

运行：`python -m unittest backend.tests.test_auth_registration.PublicAuthFlowTest.test_username_availability_reports_available_and_taken -v`

预期：FAIL，当前路由不存在并返回 404。

- [x] **步骤 3：实现最少接口代码**

在 `auth.py` 新增：

```python
class UsernameAvailabilityRequest(BaseModel):
    username: str

    @validator("username")
    def username_is_valid(cls, value):
        return validate_registration_username(value)

@router.get("/auth/username-availability")
def username_availability(request: Request, req: UsernameAvailabilityRequest = Depends(), db: DBSession = Depends(get_db)):
    if not rate_limiter.allow(client_ip(request), "username_availability", limit=60):
        raise HTTPException(429, "用户名检查过于频繁，请稍后再试")
    return {"available": db.query(User).filter(User.username == req.username).first() is None}
```

- [x] **步骤 4：运行接口测试验证通过**

运行：`python -m unittest backend.tests.test_auth_registration -v`

预期：可用、占用和格式错误场景通过，既有注册限流测试保持通过。

- [x] **步骤 5：提交后端接口**

```powershell
git add backend/routers/auth.py backend/tests/test_auth_registration.py
git commit -m "feat(注册): 查询用户名可用性"
```

### 任务 2：前端检查状态和按钮控制

**文件：**
- 修改：`frontend/src/services/api.ts:115-121`
- 创建：`frontend/src/utils/registrationAvailability.ts`
- 创建：`frontend/src/utils/registrationAvailability.test.ts`
- 修改：`frontend/src/pages/LoginPage.tsx:1-90`

- [x] **步骤 1：编写失败的状态判定测试**

创建 `registrationAvailability.test.ts`：

```ts
import { describe, expect, it } from "vitest";
import { canSubmitRegistration, usernameAvailabilityMessage } from "./registrationAvailability";

describe("registration availability", () => {
  it("keeps submission disabled while a valid username is checking", () => {
    expect(canSubmitRegistration({ usernameValid: true, usernameStatus: "checking", nameValid: true, passwordValid: true })).toBe(false);
  });
  it("only enables submission for an available username and valid fields", () => {
    expect(canSubmitRegistration({ usernameValid: true, usernameStatus: "available", nameValid: true, passwordValid: true })).toBe(true);
    expect(usernameAvailabilityMessage("taken")).toBe("该用户名已被使用，请换一个");
  });
});
```

- [x] **步骤 2：运行测试验证失败**

运行：`npm test -- registrationAvailability.test.ts`

预期：FAIL，模块尚不存在。

- [x] **步骤 3：实现最少状态辅助函数和 API 调用**

创建 `registrationAvailability.ts`，导出 `UsernameAvailabilityStatus`、`canSubmitRegistration` 和 `usernameAvailabilityMessage`；在 `api.ts` 增加：

```ts
export async function checkUsernameAvailability(username: string, signal?: AbortSignal): Promise<boolean> {
  const params = new URLSearchParams({ username });
  return (await apiJsonOrThrow<{ available: boolean }>(`/auth/username-availability?${params}`, { signal })).available;
}
```

在 `LoginPage` 使用 `useEffect`：有效用户名 400ms 后调用检查接口；输入改变和卸载时调用 `AbortController.abort()`；仅将当前请求结果写入状态。用辅助函数计算按钮可用性，显示检查中、可用、已占用和检查失败的明确文案。显示姓名为空或超过 32 位时立即提示并禁用提交；提交收到“用户名已存在”时，将用户名状态改为 `taken`，让错误定位在用户名字段。

- [x] **步骤 4：运行前端测试验证通过**

运行：`npm test -- registrationAvailability.test.ts; node --test src/services/apiResponse.test.mjs; npx tsc --noEmit`

预期：状态判定、接口错误转换和类型检查均通过。

- [x] **步骤 5：提交前端交互**

```powershell
git add frontend/src/services/api.ts frontend/src/utils/registrationAvailability.ts frontend/src/utils/registrationAvailability.test.ts frontend/src/pages/LoginPage.tsx
git commit -m "feat(注册): 即时提示用户名可用性"
```

### 任务 3：生产恢复、回归与发布

**文件：**
- 修改：`docs/DEPLOYMENT-live.md:108-117`

- [x] **步骤 1：修正生产 SQLite 目录权限**

运行：`sudo chown -R ubuntu:ubuntu /data/mathmind/app/data && sudo chmod 750 /data/mathmind/app/data && sudo chmod 640 /data/mathmind/app/data/mathmind.db && sudo systemctl restart mathmind`

预期：服务为 `active`，服务运行用户可创建 SQLite journal 文件。

- [x] **步骤 2：写入部署权限防回归说明**

在 `DEPLOYMENT-live.md` 更新解压命令，明确解压后执行 `sudo chown -R ubuntu:ubuntu /data/mathmind/app/data`，并说明不要用 root 创建持久 SQLite 目录。

- [x] **步骤 3：运行完整自动化回归**

运行：

```powershell
python -m unittest discover -s backend/tests -v
cd frontend
npm test
node --test src/services/apiResponse.test.mjs
npx tsc --noEmit
npm run build
```

预期：后端、前端、类型检查和生产构建全部通过。

- [x] **步骤 4：部署并验收正式站**

打包当前 `HEAD` 与 `frontend/dist`，上传到 `/data/mathmind/deploy.tar.gz`，使用 `sudo tar -xzf ... --no-same-owner --no-same-permissions` 解压并重启 `mathmind`。验证：本机与公网 OCR 健康接口均为 ready；`GET /api/v1/auth/username-availability?username=<随机有效名>` 返回 `available`；浏览器中已占用用户名提示明确且新用户名可成功注册。

已验证：生产服务为 `active`，本机与公网 OCR 均为 `ready`，公网有效用户名检查返回 `{"available": true}`，中文用户名返回 422 和格式文案。浏览器中格式错误即时禁用，`xingruize123` 显示“用户名可用”，7 位密码禁用、8 位密码启用；未提交表单，因此未创建验收账户。

- [x] **步骤 5：提交运维说明与验收记录**

```powershell
git add docs/DEPLOYMENT-live.md docs/superpowers/plans/2026-07-15-registration-availability.md
git commit -m "docs(部署): 固化 SQLite 写权限要求"
```
