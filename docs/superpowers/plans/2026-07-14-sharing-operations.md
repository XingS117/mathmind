# MathMind 第三期：轻量推广与运营看板实施计划

 > **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让已登录学生生成不打扰学习的专属分享链接、复制微信推广文案；管理员可查看匿名化转化与运行健康汇总。

**架构：** SQLite 保存稳定分享码、匿名访问会话与归因事件；访问链接只在浏览器本地保存分享码，注册时一次性写入归因。后台只返回聚合漏斗与引擎健康度，分享者只返回自己的总数，不暴露被邀请人或学习内容。

**技术栈：** FastAPI、SQLAlchemy、SQLite、React、Web Share API、Clipboard API。

---

## 文件结构

- 创建：`backend/models/referral.py`、`backend/services/referral_service.py`、`backend/routers/referral.py`、`backend/tests/test_referrals.py`。
- 修改：`backend/database.py`、`backend/routers/auth.py`、`backend/routers/admin.py`、`backend/main.py`。
- 创建：`frontend/src/pages/SharePage.tsx`、`frontend/src/pages/AdminOperationsPage.tsx`。
- 修改：`frontend/src/App.tsx`、`frontend/src/services/api.ts`。

## 任务 1：专属分享、归因与隐私边界

- [ ] **步骤 1：编写失败测试**

```python
def test_referral_registers_visit_then_attributes_first_registration_once(self):
    link = create_or_get_referral(db, owner_id='u_owner')
    visit = record_referral_visit(db, link.code)
    register_with_referral(db, user, visit.id)
    self.assertEqual(owner_stats(db, 'u_owner').registrations, 1)
    register_with_referral(db, user, visit.id)
    self.assertEqual(owner_stats(db, 'u_owner').registrations, 1)
```

另加：未知码不记录、分享者无法读取受邀人、注册者不得自我归因、访问/注册/首次入库/首次完成导学只各一次。

- [ ] **步骤 2：运行失败测试**

运行：`python -m unittest backend.tests.test_referrals`

预期：FAIL，模型和服务不存在。

- [ ] **步骤 3：实现最小服务与 API**

创建 `ReferralLink(owner_user_id, code unique, created_at)`、`ReferralVisit(referral_id, id random, occurred_at)`、`ReferralAttribution(inviter_user_id, invitee_user_id unique, visit_id, registered_at, first_question_at, first_tutor_completed_at)`。不保存完整 IP、UA、题目或密码。

```python
def create_or_get_referral(db, owner_id: str) -> ReferralLink: ...
def record_referral_visit(db, code: str) -> str | None: ...
def attribute_registration(db, visit_id: str, invitee_id: str) -> None: ...
def mark_first_learning_milestone(db, user_id: str, kind: str) -> None: ...
```

新增公开 `POST /referrals/visit/{code}`、登录用户 `GET /referrals/me`；注册请求可选 `referral_visit_id`，由 auth 路由调用归因。上传确认与 tutor 首次完成调用里程碑函数。所有写入幂等。

- [ ] **步骤 4：运行测试与提交**

```powershell
python -m unittest backend.tests.test_referrals
python -m unittest discover -s backend/tests -p 'test_*.py'
```

预期：`OK`。

```bash
git add backend/models/referral.py backend/services/referral_service.py backend/routers/referral.py backend/routers/auth.py backend/routers/upload.py backend/routers/tutor.py backend/database.py backend/main.py backend/tests/test_referrals.py
git commit -m "feat(推广): 增加专属分享与隐私归因"
```

## 任务 2：学生分享页与管理员聚合看板

- [ ] **步骤 1：编写失败 API/UI 契约测试**

```python
def test_admin_operations_returns_aggregate_funnel_without_invitee_identity(self):
    payload = admin_operations(request, db)
    self.assertEqual(payload['referral_funnel']['registrations'], 1)
    self.assertNotIn('invitee_user_id', str(payload))
```

- [ ] **步骤 2：运行失败测试**

运行：`python -m unittest backend.tests.test_referrals.ReferralOperationsTest`

预期：FAIL，管理员汇总端点不存在。

- [ ] **步骤 3：实现汇总、前端和分享降级**

`GET /admin/operations-overview` 返回仅聚合的分享访问、注册、首次入库、首次导学漏斗，以及现有 `RuntimeEvent` 的按特征成功率/平均耗时；不得返回受邀用户 ID、题目或完整 IP。`SharePage` 读取个人码，优先 `navigator.share`，否则复制文案和链接；文案固定为“我在数智学堂整理错题、分步练习，欢迎一起试试：<url>”。页面加载含 `?ref=code` 时先调用 visit，再将 visit id 保存在 sessionStorage，注册时带上。`AdminOperationsPage` 仅管理员可见，显示汇总卡与失败态。

- [ ] **步骤 4：验证和提交**

```powershell
python -m unittest backend.tests.test_referrals
python -m unittest discover -s backend/tests -p 'test_*.py'
cd frontend; npx tsc --noEmit; npm run build; node --test src/components/knowmapPicker.test.mjs
```

浏览器验收：手机端可复制/系统分享；ref 链接访问后注册归因；管理员只见汇总；390px 无横向溢出，控制台无错误。

```bash
git add backend/routers/admin.py frontend/src/pages/SharePage.tsx frontend/src/pages/AdminOperationsPage.tsx frontend/src/App.tsx frontend/src/services/api.ts backend/tests/test_referrals.py
git commit -m "feat(运营): 增加轻量分享与运营看板"
```

## 最终验收

- [ ] 分享不需要 AppSecret，微信内能复制文案和链接。
- [ ] 归因可统计访问、注册、首次入库、首次导学，且不泄露受邀人。
- [ ] 管理员看聚合漏斗和引擎健康度；学生只看个人汇总。
- [ ] 分享、归因与看板故障不阻塞学习链路。
- [ ] 后端全量测试、前端类型检查、构建、浏览器桌面/手机验收通过。
