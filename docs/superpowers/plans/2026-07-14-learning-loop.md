# MathMind 第二期：学习闭环完善实施计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让学生在完成导学或复习后获得可信的掌握度更新，并在首页清楚看到当天待复习任务、薄弱点和进步。

**架构：** 新建单一 `mastery_service` 负责把导学结果映射到题目的知识图谱节点、累积有界掌握分数并写回 `Mastery`。`review` 路由只完成属于当前用户的复习并调用同一服务，避免跨用户操作。`learn/dashboard` 返回可直接展示的今日复习、掌握变化和最近诊断；前端首页只消费这些结构化数据。

**技术栈：** FastAPI、SQLAlchemy、SQLite、React、TypeScript、现有 unittest/Node test。

---

## 文件结构

- 创建：`backend/services/mastery_service.py` — 节点归一化、导学/复习的幂等掌握度写回。
- 创建：`backend/tests/test_mastery_persistence.py` — 掌握度、复习权限与重复完成回归测试。
- 修改：`backend/routers/tutor.py` — 会话首次完成时持久化导学结果并防止重复排程。
- 修改：`backend/routers/review.py` — 当前用户范围内完成复习并更新掌握度。
- 修改：`backend/routers/learn.py`、`backend/schemas/api_schemas.py` — 今日任务和掌握变化响应。
- 修改：`frontend/src/services/api.ts`、`frontend/src/pages/DashboardPage.tsx`、`frontend/src/App.tsx` — 今日复习入口和刷新。

## 任务 1：掌握度持久化与安全复习完成

**文件：** 创建 `backend/services/mastery_service.py`、`backend/tests/test_mastery_persistence.py`；修改 `backend/routers/tutor.py`、`backend/routers/review.py`。

- [x] **步骤 1：编写失败测试**

```python
def test_completed_tutor_session_updates_each_question_node_once(self):
    result = apply_tutor_mastery(db, user_id='u1', question=question, session=session, delta=0.3)
    self.assertEqual(result.updated_nodes, ['node_a', 'node_b'])
    self.assertEqual(db.query(Mastery).filter_by(user_id='u1', node_id='node_a').one().score, 0.3)
    apply_tutor_mastery(db, 'u1', question, session, 0.3)
    self.assertEqual(db.query(Mastery).filter_by(user_id='u1', node_id='node_a').one().score, 0.3)

def test_user_cannot_complete_another_users_review(self):
    response = client.post('/api/v1/learn/reviews/rev_other/complete', headers=user_one_token)
    self.assertEqual(response.status_code, 404)
```

- [x] **步骤 2：运行测试验证失败**

运行：`python -m unittest backend.tests.test_mastery_persistence`

预期：FAIL，`apply_tutor_mastery` 不存在，复习完成未做用户范围过滤。

- [x] **步骤 3：实现最少服务和路由变更**

```python
def canonical_question_nodes(question: Question) -> list[str]: ...
def apply_tutor_mastery(db, user_id: str, question: Question, session: Session, delta: float) -> MasteryUpdate: ...
def apply_review_mastery(db, review: ReviewSchedule) -> MasteryUpdate: ...
```

`canonical_question_nodes` 优先使用 `knowmap_nodes`，没有时才使用知识点文本；去重并跳过空值。`apply_tutor_mastery` 在 `session.mastery_applied_at` 为空时才写入，新增该 nullable 时间列并通过现有迁移模式兼容旧库；分数限制在 0.0–1.0，增加 `total_sessions`，仅 `delta > 0` 时增加 `correct_sessions`。`tutor_message` 仅在状态从进行中首次变为完成时排 4 条复习并调用服务。复习完成查询必须同时匹配 `review_id` 和当前 `user_id`，首次完成时按轮次给 0.05 / 0.10 / 0.15 / 0.20 的上限内增量，重复提交不重复加分。

- [x] **步骤 4：运行通过测试和后端回归**

```powershell
python -m unittest backend.tests.test_mastery_persistence
python -m unittest discover -s backend/tests -p 'test_*.py'
```

预期：所有测试 `OK`。

- [x] **步骤 5：提交**

```bash
git add backend/services/mastery_service.py backend/tests/test_mastery_persistence.py backend/routers/tutor.py backend/routers/review.py backend/models/session.py backend/database.py
git commit -m "feat(学习): 持久化导学与复习掌握度"
```

## 任务 2：面向学生的今日复习与掌握反馈

**文件：** 修改 `backend/routers/learn.py`、`backend/schemas/api_schemas.py`、`frontend/src/services/api.ts`、`frontend/src/pages/DashboardPage.tsx`、`frontend/src/App.tsx`；测试 `backend/tests/test_dashboard_diagnostics.py`。

- [x] **步骤 1：编写失败 API 测试**

```python
def test_dashboard_returns_due_reviews_and_recent_mastery_change(self):
    payload = dashboard(request, db)
    self.assertEqual(payload.due_reviews[0]['id'], 'rev_due')
    self.assertEqual(payload.due_reviews[0]['question_id'], 'q1')
    self.assertEqual(payload.mastery_change, 0.3)
```

- [x] **步骤 2：运行测试验证失败**

运行：`python -m unittest backend.tests.test_dashboard_diagnostics.DashboardLearningLoopTest`

预期：FAIL，`DashboardData` 没有 `due_reviews` 与 `mastery_change`。

- [x] **步骤 3：实现最少 API 和界面**

`GET /learn/dashboard` 返回最多 3 条到期未完成复习（ID、题目 ID、轮次、类型、日期）和最近 7 天的 `mastery_change`。没有任务时返回空数组和 0。前端定义：

```ts
export type DueReview = { id: string; question_id: string; round: number; type: string; scheduled_date: string };
export const completeReview = (id: string) => apiJsonOrThrow<{ status: string }>(`/learn/reviews/${id}/complete`, { method: 'POST' });
```

`DashboardPage` 在顶部展示“今日复习”卡片：每条任务可“开始复习”并通过现有 `onSelectQuestion(question_id)` 进入导学；显示“本周掌握度变化”。完成复习操作后刷新 dashboard 和 history。无任务时显示“今日没有待复习，去入库一道题”。不可添加强制分享、排行榜或营销内容。

- [x] **步骤 4：运行前后端验证和浏览器验收**

```powershell
python -m unittest backend.tests.test_dashboard_diagnostics backend.tests.test_mastery_persistence
python -m unittest discover -s backend/tests -p 'test_*.py'
cd frontend; npx tsc --noEmit; npm run build; node --test src/components/knowmapPicker.test.mjs
```

预期：全部退出码 0。浏览器验收：桌面与 390px 下首页出现今日复习/空态；点击任务进入对应题目；完成后任务消失、掌握变化更新；控制台无错误。

- [x] **步骤 5：提交**

```bash
git add backend/routers/learn.py backend/schemas/api_schemas.py backend/tests/test_dashboard_diagnostics.py frontend/src/services/api.ts frontend/src/pages/DashboardPage.tsx frontend/src/App.tsx
git commit -m "feat(学习): 增加今日复习与掌握反馈"
```

## 最终验收

- [ ] 导学完成只写入一次掌握度并按题目图谱节点更新。
- [ ] 复习只能由所属用户完成，重复提交不会重复加分。
- [ ] 首页显示当前用户到期任务、薄弱点和最近掌握变化。
- [ ] 学生可从首页开始待复习题；桌面和手机宽度均可操作。
- [ ] 后端完整测试、前端类型检查、构建和 Node 测试全部通过。
