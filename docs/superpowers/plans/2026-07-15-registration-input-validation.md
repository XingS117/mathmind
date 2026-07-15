# 注册输入即时校验实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在注册提交前清晰提示用户名与密码规则，并让服务端和前端使用一致的注册用户名校验。

**架构：** 后端以独立用户名策略模块限制新注册账户为 3–32 位英文字母或数字；前端用纯函数模块判断同一规则，`LoginPage` 在输入时显示字段错误并阻止无效注册。API 错误转换器提取 FastAPI 验证消息，作为前端遗漏校验时的兜底。

**技术栈：** FastAPI、Pydantic、unittest、React 19、TypeScript、Vitest、Node `node:test`、Vite。

---

## 文件结构

- 创建：`backend/services/username_policy.py` — 注册用户名长度、格式常量和服务端校验函数。
- 修改：`backend/routers/auth.py` — `RegisterRequest` 复用共享用户名校验。
- 修改：`backend/tests/test_auth_registration.py` — 覆盖注册用户名边界与明确错误消息。
- 创建：`frontend/src/utils/usernamePolicy.ts` — 前端注册用户名纯函数与固定文案。
- 创建：`frontend/src/utils/usernamePolicy.test.ts` — 覆盖前端用户名边界。
- 修改：`frontend/src/pages/LoginPage.tsx` — 注册页即时字段提示、提交前拦截和禁用按钮。
- 修改：`frontend/src/services/apiResponse.js` — 将 FastAPI 422 校验列表转换成具体中文消息。
- 修改：`frontend/src/services/apiResponse.test.mjs` — 锁定 422 消息转换。

### 任务 1：建立后端注册用户名策略

**文件：**
- 创建：`backend/services/username_policy.py`
- 修改：`backend/routers/auth.py:1-45`
- 修改：`backend/tests/test_auth_registration.py:121-130`

- [x] **步骤 1：写失败的注册用户名边界测试**

在 `PublicAuthFlowTest` 增加：

```python
def test_registration_rejects_non_alphanumeric_usernames_with_explicit_message(self):
    for username in ("中文用户", "user_name", "user-name", "ab", "a" * 33):
        response = self.register(username=username)
        self.assertEqual(response.status_code, 422)
        self.assertTrue(response.json()["detail"][0]["msg"].endswith("用户名仅支持 3–32 位英文字母或数字"))

def test_registration_accepts_alphanumeric_username_boundaries(self):
    self.assertEqual(self.register(username="abc").status_code, 201)
    self.assertEqual(self.register(username="a" * 32).status_code, 201)
```

- [x] **步骤 2：运行测试确认失败**

运行：`python -m unittest backend.tests.test_auth_registration.PublicAuthFlowTest.test_registration_rejects_non_alphanumeric_usernames_with_explicit_message -v`

预期：FAIL；当前后端仍接受下划线、连字符，且旧错误文案不同。

- [x] **步骤 3：实现共享用户名策略并接入注册模型**

创建：

```python
# backend/services/username_policy.py
import re

MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 32
USERNAME_FORMAT_MESSAGE = "用户名仅支持 3–32 位英文字母或数字"
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9]{3,32}")

def validate_registration_username(value: str) -> str:
    if not USERNAME_PATTERN.fullmatch(value):
        raise ValueError(USERNAME_FORMAT_MESSAGE)
    return value
```

在 `auth.py` 删除 `re` 导入，导入 `validate_registration_username`，并将验证器替换为：

```python
@validator("username")
def username_is_valid(cls, value):
    return validate_registration_username(value)
```

将现有注册测试夹具和推广归因测试中的示例用户名从带下划线或连字符的格式改为纯字母数字，避免测试数据违背新规则。

- [x] **步骤 4：运行后端注册测试确认通过**

运行：`python -m unittest backend.tests.test_auth_registration -v`

预期：用户名边界与既有注册、登录、限流测试全部通过。

- [x] **步骤 5：提交后端策略**

```powershell
git add backend/services/username_policy.py backend/routers/auth.py backend/tests/test_auth_registration.py
git commit -m "fix(注册): 明确用户名格式规则"
```

### 任务 2：固定前端规则与 API 兜底错误消息

**文件：**
- 创建：`frontend/src/utils/usernamePolicy.ts`
- 创建：`frontend/src/utils/usernamePolicy.test.ts`
- 修改：`frontend/src/services/apiResponse.js`
- 修改：`frontend/src/services/apiResponse.test.mjs`

- [x] **步骤 1：写失败的前端策略与 422 错误转换测试**

创建 `usernamePolicy.test.ts`：

```ts
import { describe, expect, it } from "vitest";
import { USERNAME_FORMAT_MESSAGE, isRegistrationUsernameValid } from "./usernamePolicy";

describe("usernamePolicy", () => {
  it.each(["中文", "user_name", "user-name", "ab", "a".repeat(33)])("rejects %s", value => {
    expect(isRegistrationUsernameValid(value)).toBe(false);
  });
  it.each(["abc", "A1b2", "a".repeat(32)])("accepts %s", value => {
    expect(isRegistrationUsernameValid(value)).toBe(true);
  });
  it("uses the registration message", () => {
    expect(USERNAME_FORMAT_MESSAGE).toBe("用户名仅支持 3–32 位英文字母或数字");
  });
});
```

在 `apiResponse.test.mjs` 增加：

```js
test("422 验证列表会返回具体字段错误", async () => {
  await assert.rejects(
    () => jsonOrThrow(new Response(JSON.stringify({ detail: [{ msg: "Value error, 用户名仅支持 3–32 位英文字母或数字" }] }), { status: 422 })),
    { message: "用户名仅支持 3–32 位英文字母或数字" },
  );
});
```

- [x] **步骤 2：运行测试确认失败**

运行：

```powershell
Set-Location frontend
npm test
node --test src/services/apiResponse.test.mjs
```

预期：Vitest 找不到 `usernamePolicy`；Node 测试因 `jsonOrThrow` 返回“请求失败”而失败。

- [x] **步骤 3：实现纯函数与 422 消息提取**

创建：

```ts
// frontend/src/utils/usernamePolicy.ts
export const USERNAME_FORMAT_MESSAGE = "用户名仅支持 3–32 位英文字母或数字";
export const isRegistrationUsernameValid = (value: string): boolean => /^[A-Za-z0-9]{3,32}$/.test(value);
```

将 `jsonOrThrow` 的失败分支替换为：

```js
const detail = data.detail;
const validationMessage = Array.isArray(detail) && typeof detail[0]?.msg === "string" ? detail[0].msg : null;
throw new Error(typeof detail === "string" ? detail : validationMessage || "请求失败");
```

- [x] **步骤 4：运行前端策略与 API 错误测试确认通过**

运行：

```powershell
npm test
node --test src/services/apiResponse.test.mjs
```

预期：Vitest 用户名策略测试通过，Node 测试保留 503、成功和新增 422 三个场景。

- [x] **步骤 5：提交前端策略**

```powershell
git add frontend/src/utils/usernamePolicy.ts frontend/src/utils/usernamePolicy.test.ts frontend/src/services/apiResponse.js frontend/src/services/apiResponse.test.mjs
git commit -m "fix(注册): 提前提示用户名校验错误"
```

### 任务 3：接入注册页即时校验

**文件：**
- 修改：`frontend/src/pages/LoginPage.tsx`
- 修改：`frontend/src/utils/passwordPolicy.ts`（仅复用，不新增规则）

- [x] **步骤 1：定义页面字段校验状态**

在 `LoginPage.tsx` 导入：

```ts
import { isPasswordLengthValid, PASSWORD_LENGTH_MESSAGE } from "../utils/passwordPolicy";
import { isRegistrationUsernameValid, USERNAME_FORMAT_MESSAGE } from "../utils/usernamePolicy";
```

在组件内定义：

```ts
const usernameError = mode === "register" && username && !isRegistrationUsernameValid(username) ? USERNAME_FORMAT_MESSAGE : "";
const passwordError = mode === "register" && password && !isPasswordLengthValid(password) ? PASSWORD_LENGTH_MESSAGE : "";
const registrationReady = Boolean(username && name.trim() && password) && !usernameError && !passwordError;
```

- [x] **步骤 2：在提交函数中重复拦截**

在空值检查之后、网络请求之前加入：

```ts
if (mode === "register" && !isRegistrationUsernameValid(username)) {
  setError(USERNAME_FORMAT_MESSAGE);
  return;
}
if (mode === "register" && !isPasswordLengthValid(password)) {
  setError(PASSWORD_LENGTH_MESSAGE);
  return;
}
```

- [x] **步骤 3：渲染即时提示与禁用状态**

将用户名占位符改为 `用户名（3–32 位字母或数字）`；密码输入后依次渲染字段错误：

```tsx
{mode === "register" && <p style={{ fontSize: 12, color: usernameError ? "var(--error)" : "var(--muted)", margin: -8 }}>{usernameError || "用户名仅支持 3–32 位英文字母或数字"}</p>}
{mode === "register" && password && <p style={{ fontSize: 12, color: passwordError ? "var(--error)" : "var(--success)", margin: -8 }}>{passwordError || "密码长度符合要求"}</p>}
```

将注册模式按钮 `disabled` 设为 `loading || (mode === "register" && !registrationReady)`，并在禁用时设置 `cursor: "not-allowed"` 与较低 `opacity`。登录模式保持只在请求中禁用。

- [x] **步骤 4：运行前端完整检查**

运行：

```powershell
Set-Location frontend
npm test
node --test src/services/apiResponse.test.mjs
npx tsc --noEmit
npm run build
```

预期：用户名、密码纯函数与 API 错误转换测试通过，类型检查无输出，Vite 生产构建成功。

- [x] **步骤 5：提交页面交互**

```powershell
git add frontend/src/pages/LoginPage.tsx
git commit -m "feat(注册): 增加用户名与密码即时提示"
```

### 任务 4：完整回归与浏览器验收

**文件：** 无新增产品文件。

- [x] **步骤 1：执行完整自动化回归**

运行：

```powershell
python -m unittest discover -s backend/tests -v
Set-Location frontend
npm test
node --test src/services/apiResponse.test.mjs
npx tsc --noEmit
npm run build
```

预期：后端完整测试、前端 Vitest、Node 测试、类型检查和生产构建全部通过。

- [x] **步骤 2：浏览器手动验收**

在注册模式输入 `中文用户`、`user_name`、`user-name`，确认立即显示用户名规则且注册按钮不可提交；输入 `abc123` 后错误消失。输入 7 位密码确认立即显示“密码长度需为 8-128 位”，输入 8 位密码确认显示“密码长度符合要求”且在显示姓名非空时按钮可点击。切换到登录模式，确认登录按钮未被注册规则禁用。

已在本地浏览器完成：`中文用户` 显示用户名提示且按钮禁用；`abc123`、非空显示姓名和 7 位密码时显示密码提示且按钮禁用；改为 8 位密码后按钮启用。未提交注册表单，未创建验收账户。

- [x] **步骤 3：检查交付状态并提交验收记录**

运行：`git status --short`

预期：除工作区原有的 `_tmp_*` 临时文件外，无未提交的产品文件。
