# 数智学堂项目进度与接续记录

> 快照日期：2026-07-11（Public Beta · 面向真实用户可用）
> Git HEAD：`44d369a`（分支 `feat/real-question-baseline`）
> 对应方案：v1.1
> 当前状态：**已进入公开测试期 https://mathmind.xingshuwen.com/**；demo 数据已清空，第一位真实用户可从零建库；高中图谱已切人教 B 版；知识点自动挂节点；7 家模型清单已按官网更新
> 阶段归档：[`MILESTONE_2026-07-11_public-beta.md`](MILESTONE_2026-07-11_public-beta.md)
> 用途：供后续 Session、Agent 或开发者快速恢复上下文

## 1. 权威文档

- 产品定位、范围和阶段方案：[`../SPEC.md`](../SPEC.md)
- 当前进度、验证结果和恢复入口：本文档
- Agent 接续入口和当前执行门禁：[`AGENT_HANDOFF.md`](AGENT_HANDOFF.md)
- 新 Agent 可复制启动指令：[`AGENT_START_PROMPT.md`](AGENT_START_PROMPT.md)
- Phase B 历史实现计划：[`superpowers/plans/2026-06-19-phase-b-ingestion-quality.md`](superpowers/plans/2026-06-19-phase-b-ingestion-quality.md)
- 本地启动和检查命令：[`../README.md`](../README.md)

发生冲突时，以 `SPEC.md` v1.1 的产品口径和本文档的最新进度为准。

## 1.1 当前执行快照

2026-07-14 已按第二期学习闭环计划完成任务 1：导学与复习的掌握度写回现已按会话/复习记录幂等执行，复习完成按当前用户范围查询；条件更新原子 claim 防止并发重复写入，`Mastery(user_id, node_id)` 受唯一约束保护；隔离 SQLite 回归测试覆盖节点归一化、重复提交、轮次增量、双会话并发和导学会话 IDOR。任务 2 尚未开始，等待用户授权。

已完成"真实复杂题验收基线"计划全部任务，且完成 Public Beta 里程碑：

- **工作树：** `D:\Sven\maths\.worktrees\real-question-baseline`
- **分支：** `feat/real-question-baseline`
- **Git HEAD：** `44d369a`（后续以 `git rev-parse --short HEAD` 为准）
- **里程碑演进：** Alpha 5 题基线 → Beta 上线 → **Public Beta（当前）**
- **本阶段归档：** [`MILESTONE_2026-07-11_public-beta.md`](MILESTONE_2026-07-11_public-beta.md)
- **验收执行计划：** [`superpowers/plans/2026-06-27-real-question-acceptance-baseline.md`](superpowers/plans/2026-06-27-real-question-acceptance-baseline.md)
- **本地数据：** 工作树 db 副本被 Git 忽略；`.pre_*.bak` 保留了 B 版切换前的图谱与题库快照

Public Beta 阶段新增沉淀（`647ac0b..44d369a` 9 个提交，核心 4 件事）：

1. 高中图谱切人教 B 版（`d9507df` + `7fe2dab`）
2. demo 数据清空 + 新用户从零开始（`ddad385`）
3. 知识点自动挂图谱节点（`1836884`）
4. 7 家模型清单按官网更新 + MiniMax base_url 修正（`1acd50a` + `44d369a`）

（登录 + 数据隔离、正式部署、Windows 单机方案属 Beta 上线阶段成果，见 `docs/quality/ua-2026-07-09.md` UA-06 与 `docs/DEPLOYMENT-live.md`。）

任务进度：

| 任务 | 状态 | 证据 |
|------|------|------|
| 任务 1：固定案例清单 | 已完成并通过审查 | `ccd172f`、`61efeb6`；案例测试 11/11 通过 |
| 任务 2：统一评分门禁 | 完成（用户已认可） | 实现基线 `1390a9a`；TDD 修复提交 `e3c7005`；评分测试 16/16；后端完整测试 34/34 通过 |
| 任务 3：锁定现有上传与确认契约 | 完成（用户已认可） | 契约测试提交 `f1164e0`；契约测试 3/3；后端完整测试 34/34 通过；生产代码零改动 |
| 任务 4：建立验收报告骨架 | 完成 | 提交 `c90c61e`；`docs/quality/real-question-baseline-2026-06-27.md` 与 `docs/quality/cases/RQ-01..RQ-05.md` 已创建 |
| 任务 5：执行运行环境预检 | 完成 | 本次提交（见 `git log`）；总览环境表已记录，OCR `ready`；PaddleOCR 3.7 `ocr()` 真实图推理抛 `(Unimplemented) ConvertPirAttribute2RuntimeAttribute`，`/api/v1/questions/analyze` 回退 `source: manual_input`，`confidence=0` |
| 任务 6：执行 RQ-01 与 RQ-02 | 已完成（初版 + 修复包 A 后重跑） | q_5ff68b31c550 / q_52f4dbf31d39；`solution_confidence=high`；0/5、0/10 全错 → `mastery_update=0.0` |
| 任务 7：执行 RQ-03 与 RQ-04 | 完成 | q_51717033d542 / q_fde2dcfbaac8；均 90 分，无 P0 |
| 任务 8：执行 RQ-05 | 完成 | q_67928e673fbe；90 分；LLM 未照搬错标答，final=π-2 |
| 任务 9：汇总共因 + 首个修复包 | 完成 | 修复包 A 已闭环 15 条 P0/P1；见 `docs/quality/real-question-baseline-2026-06-27.md` |
| 任务 10：最终验证 + 交接 | 完成（Windows 单机方案）| backend 67 pass / knowmap 11 pass / tsc 0 error / vite build 通过；单端口托管前端已验证；`scripts/build.ps1` + `scripts/serve.ps1` + `docs/DEPLOYMENT.md` |

任务 2 修复明细：

 1. 校验 `issues` 必须是列表，每项必须是字典，`severity` 只能是 `P0`、`P1` 或 `P2`，避免拼写错误绕过 P0 门禁。
 2. 增加合法成功路径测试，证明满足门禁时 `can_progress=True`。
 3. 增加 7 个维度的独立权重测试，锁定 `15 / 15 / 20 / 10 / 20 / 15 / 5`。
 4. 校验 `tutor_completed` 必须是布尔值，并精确断言 `blocking_dimensions` 的排序。

修复包 A 已闭环：15 条 P0/P1（OCR-01/02、STARTUP-01、TUTOR-01/02/03、CONTENT-01、UX-BANNER-01、UX-01、UI-01、TUTOR-04、HINT-01、REVIEW-01、DASHBOARD-01、UX-KP-01）在 2026-07-09 修复后重跑的 5 题基线中全部验证关闭。

5 题证据：RQ-01 80/100（`q_5ff68b31c550`）、RQ-02 90/100（`q_52f4dbf31d39`）、RQ-03 90/100（`q_51717033d542`）、RQ-04 90/100（`q_fde2dcfbaac8`）、RQ-05 90/100（`q_67928e673fbe`）；均 `solution_confidence=high`、0 对时 `mastery_update=0.0`。

恢复开发时，先阅读 `docs/quality/real-question-baseline-2026-06-27.md` 的共因排序与 `docs/quality/cases/RQ-01..RQ-05.md` 的证据，再按 `AGENT_HANDOFF.md` 交接段决定下一步。

## 2. 已确认的产品口径

### 2.1 产品定位

数智学堂不是普通的拍照搜题工具，而是“错题资产管理 + 陪练教练”系统。

首页价值表达：

> 把错题变成可追踪的学习资产

MVP 主闭环：

```text
上传真实题目
  → OCR / AI 结构化
  → 人工确认入库
  → 绑定知识点
  → 分步导学
  → 记录并诊断卡点
  → 生成复习任务
  → 在图谱中追踪掌握状态
```

### 2.2 数据口径

- 当前数据库中的 14 道题全部是开发测试数据，不是真实错题。
- 这 14 道题只能证明基础页面和接口能够流转，不能证明真实题目可用。
- 真实题目通常包含几何图或函数图，题目更复杂，可能由多张图片组成。
- 后续验收必须建立至少 10 道真实、复杂、含图形的题目样本集。

### 2.3 复习周期

复习任务采用固定的 4 个间隔：

| 轮次 | 间隔 | 当前类型 |
|------|------|----------|
| 第 1 次 | 10 天 | quick |
| 第 2 次 | 30 天 | variant |
| 第 3 次 | 90 天 | comprehensive |
| 第 4 次 | 180 天 | final |

该周期是已确认的产品设计，不应改为 1 / 3 / 7 / 14 天。后续可基于掌握度调整推荐优先级，但固定周期仍作为基础计划。

## 3. 当前阶段进度

| 阶段 | 状态 | 已完成 | 尚未完成 |
|------|------|--------|----------|
| Phase A：底座与口径 | 已完成 | 前后端可构建；核心页面可运行；产品北极星和 MVP 闭环已明确；Git 仓库已建立初始基线 | 尚未配置远程仓库，当前只有本地版本历史 |
| Phase B：高质量入库 | 主要功能已实现，真实验收未完成 | 多图上传；OCR / AI 分析；人工校对；置信度提示；答案、解析、题眼编辑；图谱节点绑定；确认入库 | 真实复杂含图题样本集；图形识别质量验证；至少 10 道真实题回归 |
| Phase C：导学诊断 | 进行中 | 分步会话；尝试次数和提示记录；完成诊断摘要；仪表盘薄弱点；薄弱点定位图谱节点 | 完整卡点分类；规则失败后的 LLM 评价；5 道真实题 E2E；更多真实诊断数据 |
| Phase D：复习与掌握度 | 后端骨架 | 完成导学后生成 10 / 30 / 90 / 180 天复习记录；已有掌握度模型表 | 首页复习入口；复习执行流程；复习结果写回掌握度；图谱掌握状态；手动校正 |
| Phase E：三层变式 | 未正式开始 | 数据模型和完成页入口有少量占位能力 | 同型巩固、条件变化、综合迁移；题眼继承；自动解题校验；关联学习记录 |
| Phase F：家庭可用版 | 早期骨架 | 基础用户、登录和管理员接口 | 通用 API 携带 Token；可靠的数据隔离；家长仪表盘；备份导出；部署；使用手册 |
| Phase G：搜索与班级 | 暂缓 | 无 | 主闭环稳定后再评估 |

## 4. 本地数据快照

截至 2026-06-27：

| 数据 | 数量 | 说明 |
|------|------|------|
| 用户 | 2 | 默认用户和管理员 |
| 题目 | 14 | 全部为测试数据 |
| 学习会话 | 25 | 5 个已完成，20 个进行中 |
| 掌握度记录 | 6 | 尚未形成完整更新闭环 |
| 复习计划 | 8 | 使用 10 / 30 / 90 / 180 天间隔 |
| 含诊断摘要的会话 | 1 | 真实诊断样本明显不足 |

## 5. 最近完成的用户链路

1. 入库页支持上传一张或多张图片。
2. 系统执行 OCR / AI 分析，并进入人工校对工作台。
3. 用户可以编辑题干、题型、难度、知识点、图谱节点、题眼、答案和解析。
4. 确认后题目进入题库，并跳转到分步导学。
5. 导学完成后生成诊断摘要和复习计划。
6. 仪表盘展示最近薄弱点。
7. 点击薄弱点可进入知识图谱，并定位相关节点。

## 6. 已知技术缺口

1. 真实复杂含图题验收：5/5 通过，无 P0 遗留（修复包 A 已闭环）。
2. 当前答案判断主要依赖关键词规则，尚未实现规则失败后的 LLM 评价。
3. `mastery_update` 会返回给前端，但尚未可靠写入掌握度记录。
4. 图谱题目卡片尚未展示最近诊断、推荐原因和明确的“开始复习”入口。
5. 前端通用 API 请求没有统一附带登录 Token，登录后的数据隔离尚未真正闭环。
6. 当前所谓“变式推荐”只是选择其他已存在题目，不是三层变式生成。
7. 本地 Git 仓库已于 2026-06-27 重新初始化，初始基线提交为 `3a550e5`；尚未配置远程仓库，需注意本地磁盘故障风险。

## 7. 恢复开发时的建议顺序

开发恢复后，从 Phase C 与 Phase D 的连接点继续，不要先做部署或扩展搜索。

1. 建立真实复杂题验收集，优先包含几何图、多步骤函数题和多图题目。
2. 给图谱题目接口补充最近一次诊断和推荐原因。
3. 在图谱题目卡片增加诊断摘要与“开始复习”入口。
4. 打通复习完成结果到掌握度的持久化更新。
5. 在首页增加今日复习入口和待复习数量。
6. 用至少 5 道真实题执行完整 E2E。
7. 所有前端改动完成后，必须使用 Chrome DevTools 校验桌面端与移动端布局、溢出、交互和控制台错误。

建议首先查看以下文件：

- `backend/routers/knowmap.py`
- `backend/routers/review.py`
- `backend/routers/tutor.py`
- `backend/services/tutor_engine.py`
- `frontend/src/pages/KnowMapPage.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/services/api.ts`

## 8. 最近验证结果

2026-06-27 重新执行：

```powershell
python -m unittest discover -s backend/tests -p 'test_*.py'
python -m compileall -q backend
cd frontend
npx tsc --noEmit
npm run build
```

结果：

- 后端单元测试：4 个通过，0 个失败。
- Python 编译检查：通过。
- TypeScript 类型检查：通过。
- Vite 生产构建：通过，共转换 39 个模块。

当前 `5173` 和 `8000` 端口没有监听，前后端服务处于停止状态。

## 9. 恢复运行

后端：

```powershell
cd D:\Sven\maths
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd D:\Sven\maths\frontend
npm run dev
```

默认地址：

- 前端：`http://127.0.0.1:5173/`
- 后端健康检查：`http://127.0.0.1:8000/health`
