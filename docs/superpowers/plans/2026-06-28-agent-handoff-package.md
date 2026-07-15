# Agent 交接包实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为更换底层模型后的 Codex Agent 建立仓库内单一交接入口、强制执行规则和可直接使用的启动指令，确保它每次只执行一个批准任务并在完成后停止等待用户授权。

**架构：** 使用根目录 `AGENTS.md` 承载 Codex 的长期执行约束，使用 `docs/AGENT_HANDOFF.md` 承载项目事实和当前断点，使用 `docs/AGENT_START_PROMPT.md` 承载最短启动指令。最后更新项目状态索引，并通过路径、关键口径、交叉引用和 Git 工作树检查验证三份文件一致。

**技术栈：** Markdown、Git、PowerShell、Codex 项目指令。

---

## 文件结构

- 创建：`AGENTS.md`
  - 只记录对所有后续 Agent 长期有效的执行规则、文档读取顺序、单任务停止门和验证要求。
- 创建：`docs/AGENT_HANDOFF.md`
  - 作为人工可读的唯一交接入口，记录产品价值、权威文件、当前精确断点、当前任务范围、异常处理和完成报告模板。
- 创建：`docs/AGENT_START_PROMPT.md`
  - 只包含可直接发送给新 Agent 的启动指令，不复制项目规格。
- 修改：`docs/PROJECT_STATUS.md`
  - 在权威文档和当前执行快照中加入交接入口，澄清 `1390a9a` 是任务 2 的实现基线，不是功能分支最新文档提交。

## 执行边界

- 只创建交接治理文件，不修复任务 2，不启动任务 3。
- 不修改 `SPEC.md` v1.1 的产品口径。
- 不修改真实复杂题验收设计和原实施计划中的任务定义。
- 每个任务独立提交；完成整个交接包后停止，等待用户决定何时切换 Agent。

### 任务 1：建立 Codex 根级执行规则

**文件：**
- 创建：`AGENTS.md`
- 参考：`docs/superpowers/specs/2026-06-28-agent-handoff-governance-design.md`

- [ ] **步骤 1：确认文件尚不存在**

运行：

```powershell
Test-Path AGENTS.md
```

预期：输出 `False`。如果已存在，先读取并保留其中与本计划无冲突的用户规则，不得覆盖。

- [ ] **步骤 2：创建 `AGENTS.md`**

文件必须使用以下结构和明确措辞：

```markdown
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
```

- [ ] **步骤 3：验证根规则关键门禁**

运行：

```powershell
$required = @(
  '只执行交接文件标记的“当前允许任务”',
  '10 / 30 / 90 / 180',
  '未经用户再次明确回复“继续”，不得开始下一任务',
  'Chrome DevTools',
  '不得作为真实题验收证据'
)
foreach ($term in $required) {
  if (-not (Select-String -Path AGENTS.md -SimpleMatch $term)) {
    throw "AGENTS.md 缺少规则：$term"
  }
}
```

预期：退出码为 `0`，无异常。

- [ ] **步骤 4：检查格式并提交**

运行：

```powershell
git diff --check
git add AGENTS.md
git commit -m "docs(交接): 添加 Agent 执行规则"
```

预期：`git diff --check` 退出码为 `0`；生成一个只包含 `AGENTS.md` 的提交。

### 任务 2：建立单一交接入口

**文件：**
- 创建：`docs/AGENT_HANDOFF.md`
- 参考：`docs/PROJECT_STATUS.md`
- 参考：`docs/superpowers/specs/2026-06-28-agent-handoff-governance-design.md`

- [ ] **步骤 1：确认交接文件尚不存在**

运行：

```powershell
Test-Path docs/AGENT_HANDOFF.md
```

预期：输出 `False`。如果已存在，先核对其内容与已批准规格，不得创建第二份同用途文件。

- [ ] **步骤 2：创建交接入口的固定头部和产品口径**

文件开头必须包含：

```markdown
# MathMind Agent 交接入口

> 适用工作树：`D:\Sven\maths\.worktrees\real-question-baseline`
> 适用分支：`feat/real-question-baseline`
> 当前允许任务：任务 2，修复统一评分门禁的质量审查问题
> 下一任务：任务 3，未经用户明确回复“继续”禁止开始

## 项目价值

MathMind 不是普通的拍照搜题工具，而是“错题资产管理 + 陪练教练”系统。核心价值是把真实错题变成可追踪、可诊断、可复习的学习资产。

## 不可变事实

- 当前数据库中的 14 道题全部是开发测试数据。
- 真实验收使用 5 组复杂、含图、多页题目。
- 复习间隔固定为 `10 / 30 / 90 / 180` 天。
- 当前先验证真实题闭环，不进行部署和计划外扩展。
```

- [ ] **步骤 3：写入权威文档顺序**

必须链接以下文件，并说明冲突时不得自行改变产品方案：

```markdown
## 必读顺序

1. [`../AGENTS.md`](../AGENTS.md)
2. [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
3. [`../SPEC.md`](../SPEC.md)
4. [`superpowers/specs/2026-06-27-real-question-acceptance-baseline-design.md`](superpowers/specs/2026-06-27-real-question-acceptance-baseline-design.md)
5. [`superpowers/plans/2026-06-27-real-question-acceptance-baseline.md`](superpowers/plans/2026-06-27-real-question-acceptance-baseline.md)

产品口径以 `SPEC.md` v1.1 为准，最新执行进度以本文和 `PROJECT_STATUS.md` 的 Git 证据为准。发现实质性冲突时立即停止并报告用户。
```

- [ ] **步骤 4：写入当前断点和唯一允许范围**

必须准确记录：

```markdown
## 当前断点

- 任务 1 已完成并通过规格、质量审查：`ccd172f`、`61efeb6`。
- 任务 2 已有实现：`1390a9a`。
- 任务 2 规格审查通过，质量审查未通过。
- 暂停记录已同步到功能分支：`5474ffd`。
- Agent 交接治理规格：`9d11fff`。

## 当前只允许解决的问题

1. 严格校验 `issues` 列表、字典项和 `P0 / P1 / P2` 枚举。
2. 增加 `can_progress=True` 的合法成功路径测试。
3. 独立锁定 7 个维度权重 `15 / 15 / 20 / 10 / 20 / 15 / 5`。
4. 校验 `tutor_completed` 必须是布尔值。
5. 精确断言 `blocking_dimensions` 排序。

不得开始任务 3。任务 2 修复后必须重新执行规格审查和代码质量审查。
```

- [ ] **步骤 5：写入执行协议、停止条件和完成报告模板**

执行协议必须覆盖 TDD、专项测试、完整测试、双重审查、进度更新、Git 提交和强制停止。报告模板必须逐项包含：

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

停止条件必须包括：文档冲突、分支或数据库不一致、范围扩大、真实题数学基准冲突、计划外失败需要跨范围修复。

- [ ] **步骤 6：验证链接目标和关键内容**

运行：

```powershell
$paths = @(
  'AGENTS.md',
  'docs/PROJECT_STATUS.md',
  'SPEC.md',
  'docs/superpowers/specs/2026-06-27-real-question-acceptance-baseline-design.md',
  'docs/superpowers/plans/2026-06-27-real-question-acceptance-baseline.md'
)
foreach ($path in $paths) {
  if (-not (Test-Path $path)) { throw "缺少权威文件：$path" }
}

$required = @(
  '当前允许任务：任务 2',
  '不得开始任务 3',
  '1390a9a',
  '等待用户授权：是',
  '14 道题全部是开发测试数据'
)
foreach ($term in $required) {
  if (-not (Select-String -Path docs/AGENT_HANDOFF.md -SimpleMatch $term)) {
    throw "交接文件缺少内容：$term"
  }
}
```

预期：退出码为 `0`，全部路径存在且关键内容均可匹配。

- [ ] **步骤 7：检查格式并提交**

运行：

```powershell
git diff --check
git add docs/AGENT_HANDOFF.md
git commit -m "docs(交接): 建立 Agent 单一接续入口"
```

预期：生成一个只包含交接入口的提交。

### 任务 3：提供可直接使用的启动指令

**文件：**
- 创建：`docs/AGENT_START_PROMPT.md`
- 参考：`docs/AGENT_HANDOFF.md`

- [ ] **步骤 1：创建最短启动指令**

文件必须明确说明“提示词不承载项目事实，仓库文档才是事实源”，并提供以下可复制内容：

```markdown
# 新 Agent 启动指令

下面的指令用于把项目交给同一台电脑上的另一个 Codex Agent。项目事实以仓库文件为准，不以本提示词为准。

## 可直接发送

请接管 `D:\Sven\maths\.worktrees\real-question-baseline` 中的 MathMind 项目。

开始任何修改前：

1. 确认当前分支为 `feat/real-question-baseline`。
2. 完整阅读根目录 `AGENTS.md`。
3. 按 `docs/AGENT_HANDOFF.md` 的顺序读取所有权威文档。
4. 复述当前产品目标、不可变口径、当前允许任务、禁止事项和验收门禁。
5. 检查 Git 状态和现有测试基线。

然后只执行交接文件中的“当前允许任务”。必须按 TDD、专项测试、完整测试、规格审查、质量审查、进度更新和独立 Git 提交完成。报告证据后立即停止；未经我再次明确回复“继续”，不得开始下一任务。

如果文档、分支、数据或任务范围不一致，立即停止并报告，不要自行改方案。
```

- [ ] **步骤 2：验证启动指令没有复制易过期的任务细节**

运行：

```powershell
$forbidden = @('ccd172f', '61efeb6', '1390a9a', '15 / 15 / 20 / 10 / 20 / 15 / 5')
foreach ($term in $forbidden) {
  if (Select-String -Path docs/AGENT_START_PROMPT.md -SimpleMatch $term) {
    throw "启动指令复制了易过期事实：$term"
  }
}

$required = @('AGENTS.md', 'docs/AGENT_HANDOFF.md', '未经我再次明确回复“继续”')
foreach ($term in $required) {
  if (-not (Select-String -Path docs/AGENT_START_PROMPT.md -SimpleMatch $term)) {
    throw "启动指令缺少内容：$term"
  }
}
```

预期：退出码为 `0`。启动指令只负责路由，不形成第二份项目状态。

- [ ] **步骤 3：检查格式并提交**

运行：

```powershell
git diff --check
git add docs/AGENT_START_PROMPT.md
git commit -m "docs(交接): 添加新 Agent 启动指令"
```

预期：生成一个只包含启动指令的提交。

### 任务 4：更新状态索引并执行交接一致性验收

**文件：**
- 修改：`docs/PROJECT_STATUS.md`
- 验证：`AGENTS.md`
- 验证：`docs/AGENT_HANDOFF.md`
- 验证：`docs/AGENT_START_PROMPT.md`

- [ ] **步骤 1：在权威文档区加入交接入口**

在 `docs/PROJECT_STATUS.md` 的“权威文档”列表中加入：

```markdown
- Agent 接续入口和当前执行门禁：[`AGENT_HANDOFF.md`](AGENT_HANDOFF.md)
- 新 Agent 可复制启动指令：[`AGENT_START_PROMPT.md`](AGENT_START_PROMPT.md)
```

- [ ] **步骤 2：澄清当前执行快照中的提交含义**

将容易误解的：

```markdown
- **当前提交：** `1390a9a`
```

改为：

```markdown
- **任务 2 实现基线：** `1390a9a`
- **分支最新提交：** 运行 `git rev-parse --short HEAD` 获取；交接时以 Git 输出为准，不把文档提交号当作代码基线。
```

不要把当前 `HEAD` 的具体值写入此行，避免每次更新交接文档都造成自引用过期。

- [ ] **步骤 3：执行跨文件一致性检查**

运行：

```powershell
$files = @('AGENTS.md', 'docs/AGENT_HANDOFF.md', 'docs/AGENT_START_PROMPT.md')

foreach ($file in $files) {
  if (-not (Test-Path $file)) { throw "交接包缺少文件：$file" }
}

foreach ($file in @('AGENTS.md', 'docs/AGENT_HANDOFF.md')) {
  foreach ($term in @('10 / 30 / 90 / 180', '14 道题', 'Chrome DevTools')) {
    if (-not (Select-String -Path $file -SimpleMatch $term)) {
      throw "$file 缺少不可变口径：$term"
    }
  }
}

foreach ($file in $files) {
  if (-not (Select-String -Path $file -SimpleMatch '继续')) {
    throw "$file 缺少用户继续授权门禁"
  }
}

if (-not (Select-String -Path docs/AGENT_HANDOFF.md -SimpleMatch '当前允许任务：任务 2')) {
  throw '当前任务断点不正确'
}

git diff --check
```

预期：所有检查退出码为 `0`。

- [ ] **步骤 4：执行仓库和基线验证**

运行：

```powershell
git branch --show-current
git status --short
python -m unittest discover -s backend/tests -p 'test_*.py' -v
```

预期：

- 当前分支是 `feat/real-question-baseline`。
- 提交前只有 `docs/PROJECT_STATUS.md` 是计划内改动。
- 后端测试共 21 个，全部通过。

- [ ] **步骤 5：提交状态索引**

运行：

```powershell
git add docs/PROJECT_STATUS.md
git commit -m "docs(进度): 接入 Agent 交接入口"
```

预期：生成一个只包含项目状态索引的提交。

- [ ] **步骤 6：执行最终验收并停止**

运行：

```powershell
git status --short
git log -6 --oneline
```

预期：

- 工作树为空，无未提交修改。
- 最近提交中依次包含执行规则、交接入口、启动指令和状态索引。

向用户报告三个交接文件、后端测试结果和最新提交号，然后停止。不得开始修复任务 2。
