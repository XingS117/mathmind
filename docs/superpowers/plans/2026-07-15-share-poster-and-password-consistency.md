# 分享海报与密码规则一致性实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 统一所有密码入口为 8–128 位，并提供可保存、可转发到微信的专属邀请海报。

**架构：** 后端以单一策略校验注册、修改、管理员创建和重置密码。前端使用纯函数校验密码并生成推广文案；`SharePage` 调用浏览器 Canvas 和二维码库生成 PNG 海报。

**技术栈：** FastAPI、unittest、React 19、TypeScript、Vite、Vitest、lucide-react、qrcode。

---

## 文件结构

- 创建：`backend/services/password_policy.py` — 唯一的密码长度常量与校验函数。
- 修改：`backend/routers/auth.py`、`backend/routers/admin.py` — 复用该规则。
- 修改：`backend/tests/test_operations_admin.py` — 覆盖管理员密码边界。
- 修改：`frontend/package.json`、`frontend/package-lock.json` — qrcode、Vitest 与测试脚本。
- 创建：`frontend/src/utils/passwordPolicy.ts`、`frontend/src/utils/passwordPolicy.test.ts` — 前端密码规则和测试。
- 创建：`frontend/src/utils/sharePromotion.ts`、`frontend/src/utils/sharePromotion.test.ts` — 双人群推广文案和测试。
- 创建：`frontend/src/utils/sharePoster.ts` — PNG 海报生成、下载、系统分享。
- 修改：`frontend/src/pages/SharePage.tsx` — 推广卡和三个分享入口。
- 修改：`frontend/src/pages/SettingsPage.tsx`、`frontend/src/pages/AdminAccountsPage.tsx` — 密码文案和校验。

### 任务 1：后端统一密码策略

**文件：**
- 创建：`backend/services/password_policy.py`
- 修改：`backend/routers/auth.py`
- 修改：`backend/routers/admin.py`
- 测试：`backend/tests/test_operations_admin.py`

- [ ] **步骤 1：先写管理员密码边界失败测试**

在管理员测试类增加：

```python
def test_admin_password_endpoints_enforce_eight_to_128_characters(self):
    for password in ("a" * 7, "a" * 129):
        created = self.client.post(
            "/api/v1/admin/users",
            json={"username": f"boundary-{len(password)}", "password": password, "name": "边界用户"},
            headers=self.admin_headers,
        )
        self.assertEqual(created.status_code, 400)
        reset = self.client.post(
            f"/api/v1/admin/users/{self.user_id}/reset-password",
            json={"new_password": password}, headers=self.admin_headers,
        )
        self.assertEqual(reset.status_code, 400)
```

- [ ] **步骤 2：确认当前实现失败**

运行：`python -m unittest backend.tests.test_operations_admin -v`

预期：7 位管理员创建密码返回 200，新增测试失败。

- [ ] **步骤 3：实现共享校验**

创建：

```python
# backend/services/password_policy.py
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

def validate_password_length(value: str) -> str:
    if not MIN_PASSWORD_LENGTH <= len(value) <= MAX_PASSWORD_LENGTH:
        raise ValueError("密码长度需为 8-128 位")
    return value
```

`auth.py` 的注册验证器与修改密码均导入此函数。`admin.py` 的创建和重置路径均调用该函数，捕获 `ValueError` 后转换为 `HTTPException(400, str(exc))`。

- [ ] **步骤 4：运行密码后端回归**

运行：`python -m unittest backend.tests.test_auth_registration backend.tests.test_operations_admin backend.tests.test_security_boundaries -v`

预期：7/129 位返回 400，现有测试均通过。

- [ ] **步骤 5：提交**

```powershell
git add backend/services/password_policy.py backend/routers/auth.py backend/routers/admin.py backend/tests/test_operations_admin.py
git commit -m "fix(账户): 统一管理员密码长度规则"
```

### 任务 2：用前端纯函数固定规则与推广文案

**文件：**
- 修改：`frontend/package.json`、`frontend/package-lock.json`
- 创建：`frontend/src/utils/passwordPolicy.ts`、`frontend/src/utils/passwordPolicy.test.ts`
- 创建：`frontend/src/utils/sharePromotion.ts`、`frontend/src/utils/sharePromotion.test.ts`

- [ ] **步骤 1：安装依赖并写失败测试**

运行：

```powershell
Set-Location frontend
npm install qrcode
npm install --save-dev vitest @types/qrcode
```

在 `package.json` 加入 `"test": "vitest run"`。创建测试：

```ts
import { describe, expect, it } from "vitest";
import { isPasswordLengthValid, PASSWORD_LENGTH_MESSAGE } from "./passwordPolicy";

describe("passwordPolicy", () => {
  it.each([7, 129])("rejects %i characters", length => expect(isPasswordLengthValid("a".repeat(length))).toBe(false));
  it.each([8, 128])("accepts %i characters", length => expect(isPasswordLengthValid("a".repeat(length))).toBe(true));
  it("uses server-compatible text", () => expect(PASSWORD_LENGTH_MESSAGE).toBe("密码长度需为 8-128 位"));
});
```

```ts
import { describe, expect, it } from "vitest";
import { buildPromotionText } from "./sharePromotion";

describe("buildPromotionText", () => {
  it("keeps the referral URL and both audiences", () => {
    const text = buildPromotionText("https://example.com/?ref=mine");
    expect(text).toContain("https://example.com/?ref=mine");
    expect(text).toContain("学生");
    expect(text).toContain("家长");
  });
});
```

- [ ] **步骤 2：运行失败测试**

运行：`npm test`

预期：FAIL，两个被测模块尚不存在。

- [ ] **步骤 3：实现最小纯函数**

```ts
// frontend/src/utils/passwordPolicy.ts
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;
export const PASSWORD_LENGTH_MESSAGE = "密码长度需为 8-128 位";
export const isPasswordLengthValid = (value: string) => value.length >= PASSWORD_MIN_LENGTH && value.length <= PASSWORD_MAX_LENGTH;
```

```ts
// frontend/src/utils/sharePromotion.ts
export const SHARE_TITLE = "把每一道错题，变成下一次进步";
export function buildPromotionText(shareUrl: string): string {
  return `${SHARE_TITLE}。学生可整理错题、获得分步讲解；家长可看见学习积累和进步。一起试试数智学堂：${shareUrl}`;
}
```

- [ ] **步骤 4：运行通过测试并提交**

运行：`npm test`

预期：5 个断言通过。

```powershell
git add frontend/package.json frontend/package-lock.json frontend/src/utils/passwordPolicy.ts frontend/src/utils/passwordPolicy.test.ts frontend/src/utils/sharePromotion.ts frontend/src/utils/sharePromotion.test.ts
git commit -m "test(前端): 覆盖密码与推广文案规则"
```

### 任务 3：实现可保存的专属海报与分享页

**文件：**
- 创建：`frontend/src/utils/sharePoster.ts`
- 修改：`frontend/src/pages/SharePage.tsx`


- [ ] **步骤 1：为海报内容写失败测试**

在 `sharePromotion.test.ts` 添加：

```ts
import { buildSharePosterContent } from "./sharePromotion";

it("builds poster content from the caller referral URL", () => {
  expect(buildSharePosterContent("https://example.com/?ref=mine")).toEqual({
    title: "把每一道错题，变成下一次进步",
    studentLine: "整理错题，获得分步讲解",
    parentLine: "看见学习积累和进步",
    shareUrl: "https://example.com/?ref=mine",
  });
});
```

- [ ] **步骤 2：确认断言失败**

运行：`npm test`

预期：FAIL，`buildSharePosterContent` 尚未导出。

- [ ] **步骤 3：实现海报工具与页面交互**

在 `sharePromotion.ts` 增加 `buildSharePosterContent(shareUrl)`，返回测试中定义的 `title`、`studentLine`、`parentLine` 与原始 `shareUrl`。`sharePoster.ts` 导入该函数与 `qrcode` 的 `toCanvas`，导出：

```ts
export async function createSharePoster(shareUrl: string): Promise<Blob>;
export function downloadSharePoster(blob: Blob): void;
export async function sharePoster(blob: Blob): Promise<boolean>;
```

生成 1080×1520 Canvas：蓝色渐变背景、`文星·数智学堂`、`SHARE_TITLE`、学生/家长两行说明、280×280 的专属二维码以及换行后的链接。`canvas.toBlob` 为空时抛出 `new Error("海报生成失败，请重试")`；下载文件名固定为 `数智学堂-邀请海报.png`；仅当浏览器能分享 `File` 时使用 `navigator.share`。

`SharePage.tsx` 使用 `buildPromotionText(summary.share_url)`；用 `lucide-react` 的 `ImageDown`、`Copy`、`Share2`、`Sparkles` 制作推广卡。提供“保存微信海报”（主按钮）、“复制推广文案”和“更多分享方式”。海报成功后提示“已打开系统分享，请在微信中选择好友或朋友圈”或“海报已保存，请在微信中发送”；生成失败保留复制入口。用 `minmax(0, 1fr)` 和 `overflowWrap: "anywhere"` 保证窄屏显示。

- [ ] **步骤 4：测试、构建、提交**

运行：

```powershell
npm test
npx tsc --noEmit
npm run build
```

预期：通过且生成 `frontend/dist`。

```powershell
git add frontend/src/utils/sharePoster.ts frontend/src/utils/sharePromotion.ts frontend/src/utils/sharePromotion.test.ts frontend/src/pages/SharePage.tsx
git commit -m "feat(分享): 增加微信推广海报"
```

### 任务 4：让全部前端密码入口复用同一规则

**文件：**
- 修改：`frontend/src/pages/SettingsPage.tsx`
- 修改：`frontend/src/pages/AdminAccountsPage.tsx`
- 测试：`frontend/src/utils/passwordPolicy.test.ts`

- [ ] **步骤 1：补空字符串边界测试**

```ts
it("rejects an empty password", () => {
  expect(isPasswordLengthValid("")).toBe(false);
});
```

- [ ] **步骤 2：运行测试确认策略通过**

运行：`npm test`

预期：空字符串、7、129 位被拒绝，8、128 位通过。

- [ ] **步骤 3：替换 UI 规则与文案**

两个页面导入 `isPasswordLengthValid` 和 `PASSWORD_LENGTH_MESSAGE`。`SettingsPage` 的修改密码、管理员创建用户，及 `AdminAccountsPage` 的重置密码，统一使用：

```ts
if (!isPasswordLengthValid(passwordValue)) {
  setMsg({ status: "error", text: PASSWORD_LENGTH_MESSAGE });
  return;
}
```

`AdminAccountsPage` 的 `setMessage` 使用同一错误字符串。占位符统一为“新密码（8–128 位）”或“初始密码（8–128 位）”。

- [ ] **步骤 4：类型检查、构建与提交**

运行：

```powershell
npm test
npx tsc --noEmit
npm run build
```

预期：全部通过。

```powershell
git add frontend/src/pages/SettingsPage.tsx frontend/src/pages/AdminAccountsPage.tsx frontend/src/utils/passwordPolicy.test.ts
git commit -m "fix(账户): 统一前端密码长度提示"
```

### 任务 5：完整回归和浏览器验收

**文件：** 无新增产品文件。

- [ ] **步骤 1：执行完整自动化回归**

运行：

```powershell
python -m unittest discover -s backend/tests -v
Set-Location frontend
npm test
npx tsc --noEmit
npm run build
```

预期：全部通过。

- [ ] **步骤 2：浏览器手动验收**

以普通账户登录，确认推广卡与三个入口可见；保存的 PNG 可打开，二维码跳转到当前账户的 `share_url`，复制文本同时包含“学生”“家长”和同一链接。修改密码、创建用户、重置密码分别验证 7、8、128、129 位；所有页面显示“8–128 位”。

- [ ] **步骤 3：检查交付状态**

运行：`git status --short`

预期：仅剩工作区原有的三个 `.pre_bban.bak` 未跟踪备份文件。
