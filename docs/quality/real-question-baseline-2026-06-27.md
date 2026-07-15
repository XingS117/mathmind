# 真实复杂题验收基线

> 执行状态：complete
> 执行日期：2026-07-09（修复包 A 后重跑 5 题）
> 设计规格：`docs/superpowers/specs/2026-06-27-real-question-acceptance-baseline-design.md`

## 环境

| 项目 | 记录 |
|------|------|
| Git 基线 | 由 `git rev-parse --short HEAD` 提供 |
| 后端 `/health` | `{"status":"ok","version":"0.1.0"}` |
| OCR `/api/v1/health/ocr` | `{"status":"ready","message":"OCR 就绪"}`（PaddleOCR 3.7.0，`PP-OCRv6_medium_rec` 已加载） |
| OCR 实际推理 | ✅ 正常。5 题全部通过 `POST /api/v1/questions/analyze` 拿到 `source=ocr`、`confidence=80`、`raw_ocr_text` 非空 |
| Vision LLM 兜底 | 未触发（OCR 已识别） |
| 文本模型 | DeepSeek / deepseek-chat；`solution_confidence=high` 全部 |
| 前端 | `http://127.0.0.1:5173/`（Vite 6.4.3 dev） |
| 后端 | `http://127.0.0.1:8000/`（uvicorn） |
| 浏览器 | Chrome 150.0.7871.47 |

## 结果总览

| 案例 | 状态 | 得分 | P0 | P1 | P2 | question_id | 可进入下一阶段 |
|------|------|------|----|----|----|-------------|----------------|
| RQ-01 | complete | 80 | 0 | 0 | 2 | q_5ff68b31c550 | 是 |
| RQ-02 | complete | 90 | 0 | 0 | 2 | q_52f4dbf31d39 | 是 |
| RQ-03 | complete | 90 | 0 | 0 | 1 | q_51717033d542 | 是 |
| RQ-04 | complete | 90 | 0 | 0 | 1 | q_fde2dcfbaac8 | 是 |
| RQ-05 | complete | 90 | 0 | 0 | 2 | q_67928e673fbe | 是 |

**全部 5 题得分 ≥ 80，无 P0 遗留，共 8 条 P2 均为计划外增强项（LLM 化简与 diagram_json），不阻塞上线。**

## 共因排序（首个修复包 A 已闭环）

修复包 A 覆盖以下全部 P0/P1，均已在 2026-07-09 复跑中验证：

| ID | 根因 | 修复提交 | 验证证据 |
|----|------|----------|----------|
| P0-STARTUP-01 | OCR 初始化阻塞 startup 1-2 分钟 | `cfa4dcd` | `/health` 秒级响应 |
| P0-OCR-01 | PaddleOCR 3.x PIR/OneDNN 不兼容 `ocr()` 路径 | `1cb4b27` | 5 题 `source=ocr` |
| P0-OCR-02 | 大图并发时事件循环死锁 | `2956eb4` | 3-4 图并发 26-107s 成功 |
| P0-TUTOR-01 | `_check_answer` 关键词包含非数学等价，空 expected 判对 | `27ccf57` | 5 题 mastery 按 `completed_steps/total_steps` 计算 |
| P0-TUTOR-02 | 3 次错答直接 advance 越错越进 | `4660761` | stuck 走 `_stuck_reply` 内置去重 |
| P0-TUTOR-03 | `_complete` 无条件 `mastery=True + 0.3` | `d9c5980` | 5 题 0 对 → `mastery_update=0.0` |
| P0-CONTENT-01 | LLM `teachable_steps` 结论错误、无自检 | `f02ae77` | SOLVE_PROMPT 重写含 verification/self-confidence；5 题 `solution_confidence=high` |
| P0-UX-BANNER-01 | 零对报"学习完成" | `d9c5980` | 5 题 complete 时前端 banner 显示"未掌握"红条 |
| P0-UX-01 | 识别期浏览器无声超时 | `ee1947d` | ImageUpload 显示计时器 + OCR 心跳 + 取消按钮 |
| P1-UI-01 | 校对页图谱节点匹配失败 | `7d5cc84` + `89842a2` | 空搜索时改教材->章->节；🤖 AI 建议一键添加 |
| P1-TUTOR-04 | stuck_response + expected_answer 重复拼接 | `4660761` | 5 题 reply 无 `X X` 重复 |
| P1-HINT-01 | hint 返回完整讲解等同泄题 | `886938c` | hint ≤40 字，优先 guiding_question |
| P1-REVIEW-01 | `u_default` 被主动屏蔽 | `df5b804` | TestClient 集成测试 `test_review_default_user.py` 通过 |
| P1-DASHBOARD-01 | 薄弱点长句无法定位图谱节点 | `94a1842` | `_stuck_step_label` 截 18 字 + `findBestWeakPointNode` 滑窗匹配 |
| P1-UX-KP-01 | 知识点绑定图谱节点不便 | `89842a2` | 新增 `knowmap_matcher.py` + `suggested_nodes` + AI 建议 UI |

## 首个修复包（已闭环）

**修复包 A：入库 + 导学 + UX 三合一，共 15 条 P0/P1 全部关闭。**

- 影响案例：RQ-01/02/03/04/05
- 涉及文件：`backend/services/ocr_service.py`、`backend/services/tutor_engine.py`、`backend/services/knowmap_matcher.py`（新增）、`backend/routers/upload.py`、`backend/routers/tutor.py`、`backend/routers/review.py`、`frontend/src/components/ImageUpload.tsx`、`frontend/src/components/knowmapPicker.js`、`frontend/src/pages/TutorPage.tsx`、`frontend/src/pages/KnowMapPage.tsx`
- 回归测试范围：`backend/tests` 65 条全部通过；`frontend/src/components/knowmapPicker.test.mjs` 11 条通过。

## 遗留 P2（不阻塞上线）

- **P2-CONTENT-02**：LLM 中间步骤未强制化简为解构稿等价形式；已由新 SOLVE_PROMPT 缓解（含 verification + self-confidence），未强制阻断。
- **P2-DIAGRAM-01**：`diagram_json=null`，未生成结构化几何/函数图数据；SPEC 计划外。
- **P2-VERIFY-01**：SOLVE_PROMPT 未强制"识别原标答矛盾时标 uncertain_points"；RQ-05 恰好绕过错误标答但未主动标记。

## 结论

- 5/5 案例通过；无 P0；无 P1；仅遗留 3 类 P2 均为计划外增强项。
- 可以进入部署上线前的最终验证（任务 10）。