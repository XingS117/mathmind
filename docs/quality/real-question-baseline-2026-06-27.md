# 真实复杂题验收基线

> 执行状态：running
> 执行日期：2026-07-04
> 设计规格：`docs/superpowers/specs/2026-06-27-real-question-acceptance-baseline-design.md`

## 环境

| 项目 | 记录 |
|------|------|
| Git 基线 | c90c61e |
| 后端 `/health` | `{"status":"ok","version":"0.1.0"}` |
| OCR `/api/v1/health/ocr` | `{"status":"ready","message":"OCR 就绪"}`（PaddleOCR 3.7.0，`PP-OCRv6_medium_rec` 模型已加载） |
| OCR 实际推理 | 失败。RQ-01 第 1 张真实图报错 `(Unimplemented) ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>] (onednn_instruction.cc:118)`；`/api/v1/questions/analyze` 回退到 `source: manual_input`，`raw_ocr_text=""`，`confidence=0`，`needs_human_review=true` |
| Vision LLM 兜底 | 未触发（因为 upload.py 中触发 vision 分支需要 `part` 为空同时 `llm_config` 存在；本次运行 `source` 被设为 `manual_input`，说明既没有 OCR 文本也没有 vision 结果） |
| 文本模型 | DeepSeek / deepseek-chat（`/api/v1/settings/models/test` 连接测试未记录，见备注） |
| 前端 | `http://127.0.0.1:5173/`（Vite 6.4.3 dev 已启动） |
| 后端 | `http://127.0.0.1:8000/`（uvicorn，`Application startup complete`） |
| 浏览器 | Chrome 150.0.7871.47 |

备注：

- PaddleOCR 3.7 `PaddleOCR(...).ocr(path)` 调用在真实图片上抛 `(Unimplemented) ConvertPirAttribute2RuntimeAttribute` 异常，原因是 PaddleOCR 3.x 已把主推理入口迁移到 `predict(...)` 并采用新 PIR 执行器，旧 `ocr(...)` 路径与当前 OneDNN 后端在部分算子上不兼容。当前实施计划任务 5 只允许记录不允许改代码；本项作为跨题共同 P0 候选，等待任务 9 汇总共因时统一处理。
- 文本模型连接测试需在设置页点击"测试连接"以避免暴露 API Key；任务 6 起在真实上传流程中会自然触发文本模型，届时以 Network 面板的响应作为在用状态记录。

## 结果总览

| 案例 | 状态 | 得分 | P0 | P1 | P2 | question_id | 可进入下一阶段 |
|------|------|------|----|----|----|-------------|----------------|
| RQ-01 | complete_with_p0 | 10 | 5 | 3 | 0 | q_04f7fdacb8fc | 否 |
| RQ-02 | complete_with_p0 | 30 | 4 | 4 | 1 | q_a81566475c0f | 否 |
| RQ-03 | not_run | 0 | 0 | 0 | 0 | null | 否 |
| RQ-04 | not_run | 0 | 0 | 0 | 0 | null | 否 |
| RQ-05 | not_run | 0 | 0 | 0 | 0 | null | 否 |

## 共因排序

已在 RQ-01、RQ-02 两题上稳定复现以下跨题 P0 与 P1：

1. `P0-OCR-01`：PaddleOCR 3.7 `PaddleOCR(...).ocr(path)` 抛 `(Unimplemented) ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>] (onednn_instruction.cc:118)`；`/api/v1/questions/analyze` 稳定回退 `source: manual_input`；`raw_ocr_text=""`、`confidence=0`。相关代码：`backend/services/ocr_service.py:17,43`。
2. `P0-TUTOR-01`：`_check_answer` 只做关键词包含匹配、不判断数学等价。相关代码：`backend/services/tutor_engine.py:200-206`。
3. `P0-TUTOR-02`：连续 3 次错答直接推进到下一步（"越错越进"）；末步 stuck 会立即 `_complete`。相关代码：`backend/services/tutor_engine.py:184-186`。
4. `P0-TUTOR-03`：`_complete` 无条件 `mastery_achieved=True` + `mastery_update=0.3`，即便 `completed_steps=0`。相关代码：`backend/services/tutor_engine.py:225-235`。
5. `P0-CONTENT-01`（RQ-01 复现，RQ-02 未复现）：DeepSeek 生成的 `teachable_steps` 结论错误（RQ-01 第 3 问结论为"无实数解"，与解构稿 `t=(210-10√97)/43 或 (65-5√97)/9` 矛盾）；导学向学生传递错误答案。跨题性质待 RQ-03..RQ-05 验证。
6. `P1-UI-01`：校对页图谱节点选择器无法匹配任何节点（"没有匹配的图谱节点"），本次两题 `knowmap_nodes=[]`。
7. `P1-TUTOR-04`：`stuck_response + expected_answer` 使用同字段导致文案重复拼接（"AB=10, AE=12AB=10, AE=12"）。
8. `P1-HINT-01`：hint 直接返回该步的完整讲解（100+ 字），等同泄题。
9. `P1-REVIEW-01`：`schedule_reviews` 写入 4 条复习记录，但 `review.py:get_reviews` 主动屏蔽 `u_default`；家用默认用户看不到复习计划。

RQ-03..RQ-05 尚未跑，正式定级与首个修复包选择留给任务 9。

## 首个修复包

基线尚未执行，因此没有选定修复包。