# MathMind Agent 交接入口

> 适用工作树：`D:\Sven\maths\.worktrees\real-question-baseline`
> 适用分支：`feat/real-question-baseline`
> 当前允许任务：上线就绪（Windows 单机 + 单端口）；可直接双击 `scripts/serve.ps1` 启动
> 下一任务：按用户需要做 P2 增强 / Docker 打包 / 反代 HTTPS，均需用户明确回复

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

- 任务 1..10 已完成：5 题（RQ-01..RQ-05）验收全部通过，无 P0 遗留；修复包 A 已闭环 15 条 P0/P1。
- 5 题得分：RQ-01 80、RQ-02 90、RQ-03 90、RQ-04 90、RQ-05 90；均 `solution_confidence=high`；0 对时 `mastery_update=0.0`。
- 遗留 3 类 P2 均为计划外增强项：`CONTENT-02`（LLM 未强制化简）、`DIAGRAM-01`（无 diagram_json）、`VERIFY-01`（未强制标记原标答矛盾）。
- 2026-07-09 最终验证：backend 65 pass / knowmap 11 pass / tsc 0 error / `npm run build` 通过（39 modules，255.56 KB）。
- `rg -n "not_run|基线尚未执行" docs/quality` 无输出。
- 当前分支最新提交必须通过 `git rev-parse --short HEAD` 获取。

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

线下功能全部闭环，仅剩以下方向可开工：

1. 按用户对"部署前待用户确认的事项"的回答，编写部署脚本 / Dockerfile / systemd unit / nginx 配置。
2. 若用户要求做 P2 收敛：`CONTENT-02` 化简、`DIAGRAM-01` 结构化图形、`VERIFY-01` 原标答矛盾标注，任选其一按 TDD 推进。
3. 若用户要求 UX 复核：Chrome DevTools 桌面 1440×900 + 移动 390×844 手动跑一遍并回填证据。

未经用户回复不得选择方向。

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
