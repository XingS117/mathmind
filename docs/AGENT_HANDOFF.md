# MathMind Agent 交接入口

> 适用工作树：`D:\Sven\maths\.worktrees\real-question-baseline`
> 适用分支：`feat/real-question-baseline`
> Git HEAD（归档时刻）：`44d369a`
> 当前里程碑：**Public Beta**（面向真实用户开放，第一位真实用户可从零建库）
> 阶段归档：`MILESTONE_2026-07-11_public-beta.md`
> 下一任务：等待真实用户测试反馈；若用户未提新需求，仅在明确授权下做 P2 收敛 / MiniMax Anthropic 兼容适配 / 腾讯混元清单更新 / admin 密码等运维收尾

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

## 当前断点（Public Beta 归档时刻）

- Git HEAD：`44d369a`；分支 `feat/real-question-baseline`；未 push、未合并
- 生产：<https://mathmind.xingshuwen.com/>（腾讯云 Ubuntu 24.04，nginx + Let's Encrypt HTTPS + systemd）
- 后端：`mathmind.service` 挂 `uvicorn 127.0.0.1:8100`；前端 `frontend/dist` 由 backend 单端口托管；LLM key 从 `.env` 注入
- **Public Beta 判定通过**：demo 数据已清空、高中图谱已切人教 B 版、知识点可自动挂图谱节点、7 家模型清单已按官网更新——真实用户可以从零开始建自己的错题库
- 前两次里程碑证据：`docs/quality/real-question-baseline-2026-06-27.md`（5 题基线）+ `docs/quality/ua-2026-07-09.md`（正式上线 UA 全通）
- 本阶段完整归档：`docs/MILESTONE_2026-07-11_public-beta.md`
- 遗留 P2：`CONTENT-02` / `DIAGRAM-01` / `VERIFY-01`（均计划外增强项，不阻塞使用）
- 已知非闭环项（如需推进要用户明确授权，见归档 § 5）：MiniMax Anthropic 协议适配、腾讯混元模型清单更新、admin 默认密码 `admin123`、db 定期备份脚本、Chrome DevTools 布局最终核对
- 已知未跟踪：`data/*.pre_bban.bak`（B 版切换前的三份备份，被 `.gitignore` 匹配之外的路径命中，建议保留在本地磁盘不入库）
- 当前分支最新提交必须通过 `git rev-parse --short HEAD` 核对，不要以文档中的 hash 为准

## 部署方式（已实现）

**默认：Windows 单机 + 单端口。** 详见 `docs/DEPLOYMENT.md`。

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1   # 构建前端产物
powershell -ExecutionPolicy Bypass -File scripts\serve.ps1   # 启动生产服务
# 打开 http://127.0.0.1:8000/ 即可
```

**关键实现点：**

1. **单端口**：backend `/` 直接托管 `frontend/dist`，`/assets/*` 走 StaticFiles，非 API 的 404 走 SPA fallback（`backend/main.py`）。
2. **LLM key 迁 env**：`_get_llm_config` 优先读 `MATHMIND_LLM_API_KEY` / `DEEPSEEK_API_KEY`，其次 SQLite `UserSettings`；两条新增测试 `test_llm_env_override.py`。
3. **局域网访问**：`$env:MATHMIND_HOST="0.0.0.0"` + `scripts/serve.ps1`。
4. **开机自启**：`DEPLOYMENT.md` 有 Task Scheduler 一行命令。
5. **数据库**：`mathmind.db` 直接复制备份；干净上线时删掉重启自动 seed。

**未做的可选项（要做需用户回复）：**

- Docker / systemd（当前是 Windows PS 方案；如果用户要 Docker 打包，我可以补 `Dockerfile` + `docker-compose.yml`）。
- 反代 + HTTPS（家用局域网默认不需要；要挂公网时补 Caddyfile / nginx.conf）。
- Chrome DevTools 桌面/移动最终布局核对（我没有浏览器控制能力，需要用户手动或授权 browser skill）。
- P2 收敛：`CONTENT-02`（LLM 化简）、`DIAGRAM-01`（diagram_json）、`VERIFY-01`（原标答矛盾标注）。

## 当前只允许解决的问题

Public Beta 已上线，主闭环功能全部闭环。当前只能被动响应用户测试反馈：

1. **用户实测反馈修复**（最高优先级）：用户在生产 URL 上撞到的问题，按最小改动原则修复，改代码前先复现、有测试才合并
2. **P2 收敛**（需用户明确授权）：`CONTENT-02` 化简 / `DIAGRAM-01` 结构化图形 / `VERIFY-01` 原标答矛盾标注，任选其一按 TDD 推进
3. **模型协议适配**（需用户明确授权）：MiniMax M 系列 Anthropic 兼容适配器；腾讯混元清单更新（需用户提供静态可访问的官方文档 URL）
4. **运维收尾**（需用户明确授权）：admin 默认密码修改、db 定期备份脚本、Chrome DevTools 桌面 1440×900 + 移动 390×844 布局核对

未经用户明确授权不得自行开工，也不得把 4 个方向合成一个任务打包。

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
