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
| RQ-01 | not_run | 0 | 0 | 0 | 0 | null | 否 |
| RQ-02 | not_run | 0 | 0 | 0 | 0 | null | 否 |
| RQ-03 | not_run | 0 | 0 | 0 | 0 | null | 否 |
| RQ-04 | not_run | 0 | 0 | 0 | 0 | null | 否 |
| RQ-05 | not_run | 0 | 0 | 0 | 0 | null | 否 |

## 共因排序

基线尚未执行，因此没有已确认共因。环境预检阶段已观察到一个候选跨题共因：PaddleOCR 3.7 `ocr()` 推理在真实印刷体题目上抛 `(Unimplemented) ConvertPirAttribute2RuntimeAttribute`，以较高概率将波及 RQ-01..RQ-05 的入库阶段。正式定级留给任务 9。

## 首个修复包

基线尚未执行，因此没有选定修复包。