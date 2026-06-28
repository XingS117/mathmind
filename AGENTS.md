# MathMind Agent 执行规则

## 开始工作前

1. 只在 `D:\Sven\maths\.worktrees\real-question-baseline` 工作。
2. 确认当前分支是 `feat/real-question-baseline`。
3. 依次完整阅读：
   - `docs/AGENT_HANDOFF.md`
   - `docs/PROJECT_STATUS.md`
   - `SPEC.md`
   - `docs/superpowers/specs/2026-06-27-real-question-acceptance-baseline-design.md`
   - `docs/superpowers/plans/2026-06-27-real-question-acceptance-baseline.md`
4. 只执行交接文件标记的“当前允许任务”。

## 不可自行修改的产品口径

- 产品定位是“错题资产管理 + 陪练教练”。
- 首页价值表达是“把错题变成可追踪的学习资产”。
- 当前 14 道题都是开发测试数据，不得作为真实题验收证据。
- 真实验收题包含复杂公式、几何图或函数图，并可能由多张图片组成。
- 复习间隔固定为 `10 / 30 / 90 / 180` 天。
- 不提前部署，不扩展搜索、班级、多用户或其他计划外功能。

## 单任务停止门

- 用户每次回复“继续”只授权执行当前一个任务。
- 按 TDD 完成当前任务，运行专项测试和受影响范围的完整测试。
- 任务必须通过规格符合性审查和代码质量审查。
- 更新进度文档并创建独立 Git 提交。
- 报告证据后必须停止。未经用户再次明确回复“继续”，不得开始下一任务。

## 验证与异常

- 前端改动必须使用 Chrome DevTools 验证桌面端、移动端、控制台和网络请求。
- 没有新鲜验证证据，不得声称测试、构建、修复或审查通过。
- 不得删除、覆盖或重置用户已有改动和主目录数据库。
- 文档冲突、范围扩大、真实题基准冲突或无关测试失败需要跨范围修复时，立即停止并报告用户。
