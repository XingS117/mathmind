# Phase B：高质量入库闭环实现计划

> **面向 AI 代理的工作说明：** 必须使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

> **状态说明（2026-06-27）：** 本文件保留为 Phase B 的历史实现计划，复选框未按实际开发过程回填，不能用于判断当前进度。当前状态、验证结果和下一步入口统一以 [`../../PROJECT_STATUS.md`](../../PROJECT_STATUS.md) 为准。现有数据库中的 14 道题均为测试数据，Phase B 的真实复杂题验收尚未完成。

**目标：** 把当前“图片解析后直接确认入库”的流程，升级为可被家长和学生长期信任的高质量入库闭环。

**架构：** 保留现有 FastAPI + SQLite + React 架构。后端继续使用 `/questions/analyze` 和 `/questions/confirm` 两段式接口；前端重点改造 `ImageUpload` 为“上传 → AI 分析 → 人工校对 → 确认入库”的审核工作台。

**技术栈：** FastAPI、SQLAlchemy、SQLite、React、TypeScript、Vite。

---

## 文件结构

- 修改：`backend/models/question.py`
  - 增加入库质量状态、原始 OCR 文本、AI 分析来源、分析置信度等字段。
- 修改：`backend/schemas/api_schemas.py`
  - 增加入库分析和确认相关响应模型。
- 修改：`backend/routers/upload.py`
  - 规范 `/questions/analyze` 和 `/questions/confirm` 的输入输出。
  - 支持多图上传的文本合并策略。
- 修改：`backend/routers/knowmap.py`
  - 确认知识点绑定后，图谱题量统计准确更新。
- 修改：`frontend/src/components/ImageUpload.tsx`
  - 改造成入库审核工作台。
- 修改：`frontend/src/services/api.ts`
  - 增加类型化的 `analyzeQuestion()`、`confirmQuestion()`。
- 修改：`README.md`
  - 补充入库流程说明。

---

## 任务 1：定义入库质量数据结构

**文件：**
- 修改：`backend/models/question.py`
- 修改：`backend/schemas/api_schemas.py`

- [ ] **步骤 1：给 `Question` 增加入库质量字段**

在 `backend/models/question.py` 的 `Question` 模型中增加：

```python
raw_ocr_text = Column(Text, default="")
analysis_source = Column(String, default="manual")
analysis_confidence = Column(Integer, default=0)
review_status = Column(String, default="draft")
needs_human_review = Column(Boolean, default=True)
```

- [ ] **步骤 2：增加响应模型**

在 `backend/schemas/api_schemas.py` 增加：

```python
class QuestionAnalysisResponse(BaseModel):
    success: bool
    source: str = "manual_input"
    text: str = ""
    question_type: str = "计算题"
    knowledge_points: list[str] = []
    difficulty: int = 2
    has_diagram: bool = False
    key_insight: str = ""
    raw_ocr_text: str = ""
    confidence: int = 0
    needs_human_review: bool = True
    error: Optional[str] = None
    suggestion: Optional[str] = None

class QuestionConfirmResponse(BaseModel):
    question_id: str
    status: str
    review_status: str
    text: str
```

- [ ] **步骤 3：验证后端语法**

运行：

```bash
python -m compileall backend
```

预期：无语法错误。

---

## 任务 2：规范分析接口

**文件：**
- 修改：`backend/routers/upload.py`

- [ ] **步骤 1：统一 `/questions/analyze` 响应字段**

所有成功响应必须包含：

```json
{
  "success": true,
  "source": "ocr|vision|manual_input",
  "text": "...",
  "question_type": "计算题",
  "knowledge_points": [],
  "difficulty": 2,
  "has_diagram": false,
  "key_insight": "",
  "raw_ocr_text": "",
  "confidence": 0,
  "needs_human_review": true
}
```

- [ ] **步骤 2：支持多图文本合并**

当前接口只读取第一张图。改为遍历 `images`，对每张图执行 OCR，最后用 `\n\n--- 第 N 张 ---\n\n` 合并。

当某张图 OCR 失败时，不中断全部流程，记录为空字符串，继续处理下一张。

- [ ] **步骤 3：保留手动输入兜底**

如果 OCR 和视觉模型都没有文本，仍返回 `manual_input` 成功响应，让用户手动填题。

- [ ] **步骤 4：验证接口**

启动后端后运行：

```bash
curl http://127.0.0.1:8000/health
```

预期：返回 `{"status":"ok","version":"0.1.0"}`。

---

## 任务 3：升级确认入库接口

**文件：**
- 修改：`backend/routers/upload.py`

- [ ] **步骤 1：扩展 `ConfirmRequest`**

增加：

```python
final_answer: str = ""
solution_text: str = ""
key_insight: str = ""
knowmap_nodes: List[str] = []
analysis_source: str = "manual"
analysis_confidence: int = 0
needs_human_review: bool = False
```

- [ ] **步骤 2：保存人工确认后的字段**

创建 `Question` 时保存：

```python
raw_ocr_text=data.raw_ocr_text
analysis_source=data.analysis_source
analysis_confidence=data.analysis_confidence
review_status="complete"
needs_human_review=False
knowmap_nodes=json.dumps(data.knowmap_nodes)
final_answer=data.final_answer
```

- [ ] **步骤 3：没有 AI 解题时也允许入库**

如果没有配置模型，仍然允许以 `solution_text` 和 `final_answer` 入库；`teaching_json` 可以为空步骤，但题目状态为 `complete`。

- [ ] **步骤 4：验证确认接口**

用最小 JSON 调用 `/api/v1/questions/confirm`，预期返回 `question_id` 和 `review_status: complete`。

---

## 任务 4：前端入库审核工作台

**文件：**
- 修改：`frontend/src/components/ImageUpload.tsx`
- 修改：`frontend/src/services/api.ts`

- [ ] **步骤 1：在 `api.ts` 增加类型化方法**

增加：

```typescript
export async function analyzeQuestion(files: File[]) { ... }
export async function confirmQuestion(payload: ConfirmPayload) { ... }
```

- [ ] **步骤 2：`ImageUpload` 增加可编辑字段**

在识别结果区域展示并允许编辑：

- 题干
- 题型
- 难度
- 知识点
- 最终答案
- 解析
- 题眼
- 是否含图

- [ ] **步骤 3：显示可信度和人工确认提示**

如果 `needs_human_review` 为 `true`，显示“请先校对后入库”。

如果 `confidence < 70`，显示低置信度提示。

- [ ] **步骤 4：确认入库后跳转导学**

确认成功后调用 `onConfirm(question_id)`，进入 `TutorPage`。

- [ ] **步骤 5：前端类型检查**

运行：

```bash
npx tsc --noEmit
```

预期：无 TypeScript 错误。

---

## 任务 5：图谱绑定和题量验证

**文件：**
- 修改：`backend/routers/knowmap.py`
- 修改：`frontend/src/pages/KnowMapPage.tsx`（仅在必要时）

- [ ] **步骤 1：确认 `knowmap_nodes` 统计正确**

新增题目绑定节点后，`/knowmap/tree` 的 `question_counts` 应向父节点累加。

- [ ] **步骤 2：确认空节点不报错**

点击没有题目的节点时返回：

```json
{"questions": []}
```

而不是 404。

- [ ] **步骤 3：验证图谱接口**

运行：

```bash
curl "http://127.0.0.1:8000/api/v1/knowmap/tree?grade=高中"
```

预期：返回节点列表和 `question_counts`。

---

## 任务 6：回归验证与文档

**文件：**
- 修改：`README.md`

- [ ] **步骤 1：补充入库流程说明**

说明：

1. 上传图片。
2. AI 分析。
3. 人工校对。
4. 确认入库。
5. 进入导学。

- [ ] **步骤 2：完整验证**

运行：

```bash
cd frontend
npx tsc --noEmit
npm run build
```

运行：

```bash
python -m compileall backend
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

预期：

- 前端类型检查通过。
- 前端构建通过。
- 后端启动完成。
- `/health` 返回 ok。

- [ ] **步骤 3：人工验收场景**

用 1 道真实错题完成：

1. 上传。
2. 校对题干。
3. 填写或确认知识点。
4. 确认入库。
5. 在图谱中看到题量变化。
6. 进入导学页。

---

## 非目标

本阶段不做：

- 语义搜索。
- 班级管理。
- 云端部署。
- 复杂自适应学习路径。
- 大规模 UI 重设计。

这些能力进入 Phase G 或后续独立计划。
