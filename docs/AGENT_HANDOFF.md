# MathMind Agent 交接入口

> 适用工作树：`D:\Sven\maths\.worktrees\real-question-baseline`
> 适用分支：`feat/real-question-baseline`
> 当前允许任务：任务 7，执行 RQ-03 与 RQ-04（等待用户明确回复"继续"授权）
> 下一任务：任务 8，未经用户明确回复"继续"禁止开始

## 项目价值

MathMind 不是普通的拍照搜题工具，而是“错题资产管理 + 陪练教练”系统。核心价值是把真实错题变成可追踪、可诊断、可复习的学习资产。

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

## 不可变事实

- 当前数据库中的 14 道题全部是开发测试数据，不能作为真实题验收证据。
- 真实验收使用 5 组复杂、含图、多页题目。
- 真实题可能包含复杂公式、几何图、函数图和多张图片。
- 复习间隔固定为 `10 / 30 / 90 / 180` 天。
- 当前先验证真实题闭环，不进行部署和计划外扩展。
- 前端改动完成后必须使用 Chrome DevTools 验证桌面端、移动端、控制台和网络请求。

## 必读顺序

1. [`../AGENTS.md`](../AGENTS.md)
2. [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
3. [`../SPEC.md`](../SPEC.md)
4. [`superpowers/specs/2026-06-27-real-question-acceptance-baseline-design.md`](superpowers/specs/2026-06-27-real-question-acceptance-baseline-design.md)
5. [`superpowers/plans/2026-06-27-real-question-acceptance-baseline.md`](superpowers/plans/2026-06-27-real-question-acceptance-baseline.md)

产品口径以 `SPEC.md` v1.1 为准，最新执行进度以本文和 `PROJECT_STATUS.md` 的 Git 证据为准。发现实质性冲突时立即停止并报告用户，不得自行改变产品方案。

## 当前断点

- 任务 1..4 已完成并通过审查（见 PROJECT_STATUS）。
- 任务 5 已完成：环境预检提交 `60df039`；`/health` ok、`/api/v1/health/ocr` ready；PaddleOCR 3.7 `ocr()` 真实图推理抛 `(Unimplemented) ConvertPirAttribute2RuntimeAttribute`。
- 任务 6 已完成：RQ-01（`q_04f7fdacb8fc` / `s_35baaff4ebff` / 10 步）与 RQ-02（`q_a81566475c0f` / `s_afe97ec72ce2` / 9 步）全链路通过 API 直调完成。两题均在一路错答下被系统判 complete、`mastery_update=0.3`、`completed_steps=0`。
- 已确认 5 条跨题 P0：`OCR-01`（PaddleOCR PIR/OneDNN 不兼容）、`TUTOR-01`（关键词匹配非数学等价）、`TUTOR-02`（越错越进）、`TUTOR-03`（无条件 mastery=True）、`CONTENT-01`（RQ-01 复现，LLM 数学结论错误）。
- 4 条跨题 P1：`UI-01`（校对页图谱节点匹配失败）、`TUTOR-04`（stuck 文案重复拼接）、`HINT-01`（提示泄题）、`REVIEW-01`（默认用户看不到复习计划）。
- 1 条 P2：`CONTENT-02`（LLM 分步答案未化简）。
- 当前分支最新提交必须通过 `git rev-parse --short HEAD` 获取，不得把上述历史证据误认为当前 `HEAD`。

任务 7 至任务 10 均未开始。

## 当前只允许解决的问题

任务 6 已完成（本次提交，见 `git log`）：`docs/quality/cases/RQ-01.md`、`RQ-02.md`、`docs/quality/real-question-baseline-2026-06-27.md` 已按真实证据填写；实施计划任务 6 六个复选框全部勾选；追加 2026-07-04 任务 6 执行快照。零代码改动。

任务 7（RQ-03 + RQ-04）尚未授权。执行任务 7 时只允许：

1. 按 `data/acceptance/real-question-cases.json` 的 RQ-03、RQ-04 图片顺序调 `POST /api/v1/questions/analyze`（前端 UI-01 未修复前继续走 API 直调）。
2. 用解构稿字段调 `POST /api/v1/questions/confirm` 完成入库；记录 `question_id`。
3. 每题跑一次 tutor 5 分支：错答 → 提示 → 连续 2 次不知道 → 一路错答直到 complete；记录 `session_id`、`diagnostic_summary`。
4. 按证据在 `docs/quality/cases/RQ-03.md`、`RQ-04.md` 打 0/1/2 分并记录 P0/P1/P2；对 `CONTENT-01` 是否复现给出结论。
5. 只覆盖 RQ-03、RQ-04；不得同时推进 RQ-05；不得改动生产代码。

未经用户明确回复"继续"，不得开始任务 7。

## 单任务执行协议

用户每次回复“继续”只授权执行当前一个任务。当前任务必须依次完成：

1. 完整阅读任务要求及相关代码，确认工作树、分支和 Git 状态。
2. 按 TDD 先编写能暴露问题的失败测试，并确认测试因预期原因失败。
3. 只实现让当前测试通过所需的最小改动。
4. 运行当前任务的专项测试。
5. 运行受影响范围的完整测试。
6. 执行规格符合性审查。
7. 执行代码质量审查。
8. 修复阻断性审查意见，并重新运行相关验证。
9. 更新 `PROJECT_STATUS.md` 和原实施计划的执行快照。
10. 创建只包含当前任务改动的独立 Git 提交。
11. 使用本文的完成报告模板汇报，然后立即停止。

测试通过、审查通过或 Agent 自己认为可以继续，都不能替代用户明确回复“继续”。

## 禁止事项

- 不得在任务 2 质量审查通过前开始任务 3。
- 不得自行改变任务顺序、评分口径、产品定位或复习间隔。
- 不得把 14 道开发测试题包装成真实题验收结果。
- 不得提前部署或扩展搜索、班级、多用户、三层变式等计划外范围。
- 不得删除、覆盖、重置用户已有改动或主目录数据库。
- 不得只依据 Agent 的口头判断宣称完成，所有结论必须有新鲜验证证据。

## 必须停止并报告的情况

出现以下任一情况时立即停止，不得自行扩大范围：

- 权威文档之间存在无法按优先级消解的矛盾。
- 当前分支、工作树、Git 状态或数据库副本与交接记录不一致。
- 完成当前任务需要修改下一个任务的范围。
- 真实题、人工基准或数学结论存在冲突。
- 计划外测试失败，且修复需要引入额外功能或跨任务改动。
- 用户的新要求会改变已确认的产品口径、验收标准或任务顺序。

报告必须说明发现的事实、影响范围、可选处理方式和推荐方案，然后等待用户决定。

## 完成报告模板

```text
任务：
状态：完成 / 阻塞
本次修改：
专项测试：
完整测试：
规格审查：
质量审查：
Chrome DevTools 验证：不适用 / 验证结果
Git 提交：
剩余风险：
下一任务：
等待用户授权：是
```

任何验证未执行时必须明确写“未执行”和原因，不得使用“应该通过”等推测性表述。
