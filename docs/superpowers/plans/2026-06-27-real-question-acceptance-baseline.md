# 真实复杂题验收基线实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 使用 5 组固定真实复杂题验证当前“多图入库 → 人工校对 → 导学 → 诊断”链路，形成可复现的评分基线和按 P0/P1/P2 排序的问题清单。

**架构：** 不预先改造生产逻辑。先在 `tools/` 中建立独立的案例清单校验和评分工具，再用自动化测试锁定现有上传、确认和诊断行为，最后通过现有 React 页面和 FastAPI 接口逐题执行人工验收。审计结束后只选择影响面最大的一个根因进入后续修复计划。

**技术栈：** Python 3.12、`unittest`、FastAPI、SQLAlchemy、SQLite、React、TypeScript、Chrome DevTools、Markdown。

---

## 执行快照（2026-06-28 暂停）

执行位置：

- 工作树：`D:\Sven\maths\.worktrees\real-question-baseline`
- 分支：`feat/real-question-baseline`
- 当前提交：`1390a9a`

当前进度：

| 任务 | 状态 | 提交 / 验证 |
|------|------|-------------|
| 任务 1：固定案例清单 | 完成，规格与质量审查通过 | `ccd172f`、`61efeb6`；案例测试 11/11 |
| 任务 2：统一评分门禁 | 实现完成，规格审查通过，质量审查要求修复 | `1390a9a`；评分测试 6/6；后端完整测试 21/21 |
| 任务 3 至任务 10 | 未开始 | 等待任务 2 质量门通过 |

任务 2 恢复动作：

1. 使用 TDD 为 `issues` 结构和 `severity` 枚举增加校验，防止错误字段绕过 P0 门禁。
2. 增加 `can_progress=True` 的合法成功路径测试。
3. 分别锁定 7 个维度的独立权重。
4. 校验 `tutor_completed` 为布尔值，精确测试阻断维度排序。
5. 运行评分专项测试和后端完整测试。
6. 提交修复后重新执行规格审查与代码质量审查。

在质量审查通过前，不得开始任务 3。

## 执行快照（2026-06-30 任务 2 质量审查 TDD 修复）

执行位置：

- 工作树：`D:\Sven\maths\.worktrees\real-question-baseline`
- 分支：`feat/real-question-baseline`
- 任务 2 实现基线：`1390a9a`
- 分支最新提交：运行 `git rev-parse --short HEAD` 获取；文档不得代替 Git 输出。

当前进度：

| 任务 | 状态 | 提交 / 验证 |
|------|------|-------------|
| 任务 1：固定案例清单 | 完成，规格与质量审查通过 | `ccd172f`、`61efeb6`；案例测试 11/11 |
| 任务 2：统一评分门禁 | 实现完成、规格审查通过、质量审查 TDD 修复完成，待重新审查 | 实现基线 `1390a9a`；本次 TDD 修复提交见 `git log` 最新提交；评分测试 16/16；后端完整测试 31/31 |
| 任务 3 至任务 10 | 未开始 | 等待任务 2 质量审查重新执行通过 |

任务 2 质量审查 TDD 修复明细：

1. 新增 `_validate_issues`：显式校验 `issues` 必须是列表、每项必须是字典、`severity` 只能是 `P0/P1/P2`。
2. `evaluate_case` 增加 `isinstance(tutor_completed, bool)` 校验，非布尔值抛出 `TypeError`。
3. 新增 10 个专项测试：列表/字典/严重度/合法成功路径/P1 不阻断/独立权重/布尔类型/排序断言。
4. 修复后所有规格符合性审查与代码质量审查项均通过；无 P0/P1 剩余。

在任务 2 质量审查重新执行通过前，不得开始任务 3。

---

## 执行边界

- 设计依据：`docs/superpowers/specs/2026-06-27-real-question-acceptance-baseline-design.md`
- 当前分支基线：`45fed0c`
- 当前模型配置：DeepSeek 文本模型已配置，API Key 存在。
- OCR 环境：`paddleocr`、`paddle`、`cv2` 模块已安装；运行时初始化仍需通过真实请求验证。
- 本计划不修改 OCR、视觉识别、导学或复习业务逻辑。
- 如果自动测试暴露现有行为不符合设计，只记录问题，不在本计划中顺手修复。
- 新增真实题不得删除或覆盖原有 14 道测试题，所有新 `question_id` 必须记录到逐题报告。
- 涉及前端操作时必须使用 Chrome DevTools 检查页面、网络请求和控制台。

## 文件结构

### 新建

- `tools/__init__.py`
  - 将验收工具目录声明为 Python 包。
- `tools/acceptance_cases.py`
  - 加载并校验固定案例清单、必填字段、图片顺序和文件存在性。
- `tools/acceptance_scoring.py`
  - 计算 100 分制得分并执行单题通过判定。
- `data/acceptance/real-question-cases.json`
  - 保存 RQ-01 至 RQ-05 的原图顺序、对照材料和风险标签。
- `backend/tests/test_acceptance_cases.py`
  - 验证案例清单完整性和路径有效性。
- `backend/tests/test_acceptance_scoring.py`
  - 验证权重、得分和 P0 门禁规则。
- `backend/tests/test_upload_contract.py`
  - 锁定多图顺序、非法 LLM JSON 回退和确认入库持久化行为。
- `docs/quality/real-question-baseline-2026-06-27.md`
  - 保存 5 题总览、得分、问题等级和修复优先级。
- `docs/quality/cases/RQ-01.md`
- `docs/quality/cases/RQ-02.md`
- `docs/quality/cases/RQ-03.md`
- `docs/quality/cases/RQ-04.md`
- `docs/quality/cases/RQ-05.md`
  - 保存每道题的输入、原始分析、人工修改、导学过程和诊断结果。

### 修改

- `docs/PROJECT_STATUS.md`
  - 记录基线审计结果和下一个修复包。

### 不修改

- `backend/routers/upload.py`
- `backend/services/ocr_service.py`
- `backend/services/tutor_engine.py`
- `frontend/src/components/ImageUpload.tsx`
- 其他生产业务代码

如果审计发现这些文件存在问题，只在报告中记录，后续单独创建修复计划。

---

### 任务 1：建立固定案例清单

**文件：**

- 创建：`tools/__init__.py`
- 创建：`tools/acceptance_cases.py`
- 创建：`data/acceptance/real-question-cases.json`
- 测试：`backend/tests/test_acceptance_cases.py`

- [ ] **步骤 1：编写失败的案例清单测试**

创建 `backend/tests/test_acceptance_cases.py`：

```python
import unittest

from tools.acceptance_cases import load_acceptance_cases


EXPECTED_IDS = ["RQ-01", "RQ-02", "RQ-03", "RQ-04", "RQ-05"]
EXPECTED_IMAGE_COUNTS = {
    "RQ-01": 3,
    "RQ-02": 4,
    "RQ-03": 3,
    "RQ-04": 2,
    "RQ-05": 3,
}


class AcceptanceCasesTest(unittest.TestCase):
    def test_manifest_contains_fixed_cases_in_order(self):
        cases = load_acceptance_cases()

        self.assertEqual([case["case_id"] for case in cases], EXPECTED_IDS)
        self.assertEqual(
            {case["case_id"]: len(case["images"]) for case in cases},
            EXPECTED_IMAGE_COUNTS,
        )

    def test_every_case_file_exists(self):
        cases = load_acceptance_cases()

        for case in cases:
            self.assertTrue(case["reference_path"].is_file(), case["case_id"])
            for image in case["image_paths"]:
                self.assertTrue(image.is_file(), f"{case['case_id']}: {image}")

    def test_page_order_is_explicit_and_stable(self):
        cases = load_acceptance_cases()

        for case in cases:
            expected_pages = list(range(1, len(case["images"]) + 1))
            self.assertEqual(
                [image["page"] for image in case["images"]],
                expected_pages,
                case["case_id"],
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试并确认失败**

运行：

```powershell
python -m unittest backend.tests.test_acceptance_cases -v
```

预期：FAIL，报错 `ModuleNotFoundError: No module named 'tools.acceptance_cases'`。

- [ ] **步骤 3：创建案例加载与校验工具**

创建空文件 `tools/__init__.py`。

创建 `tools/acceptance_cases.py`：

```python
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "acceptance" / "real-question-cases.json"
REQUIRED_FIELDS = {"case_id", "title", "images", "reference", "capabilities", "risks"}


def load_acceptance_cases(manifest_path: Path = DEFAULT_MANIFEST) -> list[dict]:
    with manifest_path.open(encoding="utf-8") as handle:
        cases = json.load(handle)

    if not isinstance(cases, list) or not cases:
        raise ValueError("Acceptance manifest must contain a non-empty list")

    seen_ids: set[str] = set()
    normalized: list[dict] = []
    for case in cases:
        missing = REQUIRED_FIELDS - set(case)
        if missing:
            raise ValueError(f"{case.get('case_id', 'unknown')} missing fields: {sorted(missing)}")
        if case["case_id"] in seen_ids:
            raise ValueError(f"Duplicate case_id: {case['case_id']}")
        seen_ids.add(case["case_id"])

        pages = [image["page"] for image in case["images"]]
        if pages != list(range(1, len(case["images"]) + 1)):
            raise ValueError(f"{case['case_id']} pages must be sequential from 1")

        normalized_case = dict(case)
        normalized_case["image_paths"] = [
            PROJECT_ROOT / image["path"] for image in case["images"]
        ]
        normalized_case["reference_path"] = PROJECT_ROOT / case["reference"]
        normalized.append(normalized_case)

    return normalized
```

- [ ] **步骤 4：创建完整案例清单**

创建 `data/acceptance/real-question-cases.json`：

```json
[
  {
    "case_id": "RQ-01",
    "title": "几何变换与动点问题综合探究",
    "images": [
      {
        "page": 1,
        "path": "数学错题/原题目/5.10-几何变换与动点问题综合探究（平移、面积函数与直角三角形存在性）1.jpg"
      },
      {
        "page": 2,
        "path": "数学错题/原题目/5.10-几何变换与动点问题综合探究（平移、面积函数与直角三角形存在性）2.jpg"
      },
      {
        "page": 3,
        "path": "数学错题/原题目/5.10-几何变换与动点问题综合探究（平移、面积函数与直角三角形存在性）3.jpg"
      }
    ],
    "reference": "数学错题/解构后/5.10-几何变换与动点问题综合探究（平移、面积函数与直角三角形存在性）.md",
    "capabilities": ["多图合并", "复杂图形", "分段函数", "存在性问题"],
    "risks": ["点位关系丢失", "运动区间遗漏", "多问合并错误"]
  },
  {
    "case_id": "RQ-02",
    "title": "二次函数综合探究",
    "images": [
      {
        "page": 1,
        "path": "数学错题/原题目/5.10-二次函数综合探究：平移、弦长与动点距离最值问题1.jpg"
      },
      {
        "page": 2,
        "path": "数学错题/原题目/5.10-二次函数综合探究：平移、弦长与动点距离最值问题2.jpg"
      },
      {
        "page": 3,
        "path": "数学错题/原题目/5.10-二次函数综合探究：平移、弦长与动点距离最值问题3.jpg"
      },
      {
        "page": 4,
        "path": "数学错题/原题目/5.10-二次函数综合探究：平移、弦长与动点距离最值问题4.jpg"
      }
    ],
    "reference": "数学错题/解构后/5.10-二次函数综合探究：平移、弦长与动点距离最值问题.md",
    "capabilities": ["公式识别", "参数关系", "函数平移", "距离最值"],
    "risks": ["上下标错误", "分式错误", "答案页并入题干"]
  },
  {
    "case_id": "RQ-03",
    "title": "四边形折叠中的相似与隐圆最值",
    "images": [
      {
        "page": 1,
        "path": "数学错题/原题目/5.1-四边形折叠中的相似与隐圆最值综合题1.jpg"
      },
      {
        "page": 2,
        "path": "数学错题/原题目/5.1-四边形折叠中的相似与隐圆最值综合题2.jpg"
      },
      {
        "page": 3,
        "path": "数学错题/原题目/5.1-四边形折叠中的相似与隐圆最值综合题3.jpg"
      }
    ],
    "reference": "数学错题/解构后/5.1-四边形折叠中的相似与隐圆最值综合题.md",
    "capabilities": ["多子图", "折叠语义", "相似关系", "隐圆最值"],
    "risks": ["撇号点名丢失", "图号与条件错配", "折叠前后点混淆"]
  },
  {
    "case_id": "RQ-04",
    "title": "K 型全等模型在一次函数中的综合探究",
    "images": [
      {
        "page": 1,
        "path": "数学错题/原题目/5.10-“K型全等”模型在一次函数中的综合探究1.jpg"
      },
      {
        "page": 2,
        "path": "数学错题/原题目/5.10-“K型全等”模型在一次函数中的综合探究2.jpg"
      }
    ],
    "reference": "数学错题/解构后/5.10-“K型全等”模型在一次函数中的综合探究.md",
    "capabilities": ["坐标图", "模型迁移", "旋转", "分类讨论"],
    "risks": ["坐标轴信息丢失", "象限条件遗漏", "旋转方向错误"]
  },
  {
    "case_id": "RQ-05",
    "title": "圆的切线判定与阴影面积",
    "images": [
      {
        "page": 1,
        "path": "数学错题/原题目/5.10-圆的切线判定与阴影面积综合题1.jpg"
      },
      {
        "page": 2,
        "path": "数学错题/原题目/5.10-圆的切线判定与阴影面积综合题2.jpg"
      },
      {
        "page": 3,
        "path": "数学错题/原题目/5.10-圆的切线判定与阴影面积综合题3.jpg"
      }
    ],
    "reference": "数学错题/解构后/5.10-圆的切线判定与阴影面积综合题.md",
    "capabilities": ["圆中角关系", "切线判定", "阴影面积", "错误答案识别"],
    "risks": ["原标答逻辑矛盾", "图形条件误读", "错误结论被照搬"]
  }
]
```

- [ ] **步骤 5：运行案例清单测试**

运行：

```powershell
python -m unittest backend.tests.test_acceptance_cases -v
```

预期：3 个测试全部通过。

- [ ] **步骤 6：提交案例清单**

```powershell
git add tools/__init__.py tools/acceptance_cases.py data/acceptance/real-question-cases.json backend/tests/test_acceptance_cases.py
git commit -m "test(验收): 建立真实复杂题固定清单"
```

---

### 任务 2：建立统一评分门禁

**文件：**

- 创建：`tools/acceptance_scoring.py`
- 测试：`backend/tests/test_acceptance_scoring.py`

- [ ] **步骤 1：编写失败的评分测试**

创建 `backend/tests/test_acceptance_scoring.py`：

```python
import unittest

from tools.acceptance_scoring import evaluate_case, weighted_score


PASSING_SCORES = {
    "multi_image": 2,
    "text_formula": 2,
    "diagram_semantics": 2,
    "structured_fields": 1,
    "solution_consistency": 2,
    "tutor_quality": 1,
    "diagnostic_quality": 2,
}


class AcceptanceScoringTest(unittest.TestCase):
    def test_weighted_score_uses_design_weights(self):
        self.assertEqual(weighted_score(PASSING_SCORES), 87.5)

    def test_p0_issue_blocks_progress_even_with_high_score(self):
        result = evaluate_case(
            scores={key: 2 for key in PASSING_SCORES},
            issues=[{"severity": "P0", "summary": "题干漏掉第三问"}],
            tutor_completed=True,
        )

        self.assertFalse(result["can_progress"])
        self.assertEqual(result["score"], 100.0)

    def test_zero_in_critical_dimension_blocks_progress(self):
        scores = dict(PASSING_SCORES)
        scores["diagram_semantics"] = 0

        result = evaluate_case(scores=scores, issues=[], tutor_completed=True)

        self.assertFalse(result["can_progress"])
        self.assertIn("diagram_semantics", result["blocking_dimensions"])

    def test_score_below_80_blocks_progress(self):
        scores = {key: 1 for key in PASSING_SCORES}

        result = evaluate_case(scores=scores, issues=[], tutor_completed=True)

        self.assertEqual(result["score"], 50.0)
        self.assertFalse(result["can_progress"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试并确认失败**

运行：

```powershell
python -m unittest backend.tests.test_acceptance_scoring -v
```

预期：FAIL，报错 `ModuleNotFoundError: No module named 'tools.acceptance_scoring'`。

- [ ] **步骤 3：实现最小评分工具**

创建 `tools/acceptance_scoring.py`：

```python
WEIGHTS = {
    "multi_image": 15,
    "text_formula": 15,
    "diagram_semantics": 20,
    "structured_fields": 10,
    "solution_consistency": 20,
    "tutor_quality": 15,
    "diagnostic_quality": 5,
}

CRITICAL_DIMENSIONS = {
    "multi_image",
    "text_formula",
    "diagram_semantics",
    "solution_consistency",
}


def weighted_score(scores: dict[str, int]) -> float:
    if set(scores) != set(WEIGHTS):
        missing = sorted(set(WEIGHTS) - set(scores))
        extra = sorted(set(scores) - set(WEIGHTS))
        raise ValueError(f"Score dimensions mismatch; missing={missing}, extra={extra}")
    invalid = {key: value for key, value in scores.items() if value not in (0, 1, 2)}
    if invalid:
        raise ValueError(f"Scores must be 0, 1, or 2: {invalid}")
    return round(sum((scores[key] / 2) * WEIGHTS[key] for key in WEIGHTS), 1)


def evaluate_case(
    scores: dict[str, int],
    issues: list[dict],
    tutor_completed: bool,
) -> dict:
    score = weighted_score(scores)
    blocking_dimensions = sorted(
        dimension for dimension in CRITICAL_DIMENSIONS if scores[dimension] == 0
    )
    has_p0 = any(issue.get("severity") == "P0" for issue in issues)
    can_progress = (
        score >= 80
        and not has_p0
        and not blocking_dimensions
        and tutor_completed
    )
    return {
        "score": score,
        "has_p0": has_p0,
        "blocking_dimensions": blocking_dimensions,
        "tutor_completed": tutor_completed,
        "can_progress": can_progress,
    }
```

- [ ] **步骤 4：运行评分测试**

运行：

```powershell
python -m unittest backend.tests.test_acceptance_scoring -v
```

预期：4 个测试全部通过。

- [ ] **步骤 5：提交评分工具**

```powershell
git add tools/acceptance_scoring.py backend/tests/test_acceptance_scoring.py
git commit -m "test(验收): 添加真实题评分门禁"
```

---

### 任务 3：锁定现有上传与确认契约

**文件：**

- 创建：`backend/tests/test_upload_contract.py`

- [ ] **步骤 1：编写多图顺序特征测试**

在 `backend/tests/test_upload_contract.py` 中加入：

```python
import json
import unittest
from io import BytesIO
from unittest.mock import AsyncMock, patch

from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models.question import Question
from backend.routers.upload import ConfirmRequest, analyze_question, confirm_question


class UploadContractTest(unittest.IsolatedAsyncioTestCase):
    async def test_multi_image_ocr_text_preserves_upload_order(self):
        images = [
            UploadFile(filename="page-1.jpg", file=BytesIO(b"page-1")),
            UploadFile(filename="page-2.jpg", file=BytesIO(b"page-2")),
        ]

        with (
            patch(
                "backend.routers.upload.ocr_image",
                new=AsyncMock(side_effect=["第一页题干", "第二页答案"]),
            ),
            patch(
                "backend.routers.upload._get_llm_config",
                return_value=(False, None),
            ),
        ):
            result = await analyze_question(images=images, request=None)

        self.assertTrue(result["success"])
        self.assertEqual(result["source"], "ocr")
        self.assertEqual(
            result["raw_ocr_text"],
            "--- 第 1 张 ---\n第一页题干\n\n--- 第 2 张 ---\n第二页答案",
        )

    async def test_invalid_llm_json_keeps_raw_ocr_text(self):
        images = [UploadFile(filename="page-1.jpg", file=BytesIO(b"page-1"))]
        config = {
            "model_provider": "deepseek",
            "model_name": "deepseek-chat",
            "api_key": "test-key",
            "base_url": "https://example.invalid",
        }

        with (
            patch(
                "backend.routers.upload.ocr_image",
                new=AsyncMock(return_value="原始 OCR 文本"),
            ),
            patch(
                "backend.routers.upload._get_llm_config",
                return_value=(True, config),
            ),
            patch(
                "backend.routers.upload.call_llm_with_config",
                new=AsyncMock(return_value="不是 JSON"),
            ),
        ):
            result = await analyze_question(images=images, request=None)

        self.assertTrue(result["success"])
        self.assertEqual(result["text"], "原始 OCR 文本")
        self.assertEqual(result["raw_ocr_text"], "原始 OCR 文本")
        self.assertEqual(result["confidence"], 40)
        self.assertTrue(result["needs_human_review"])
```

- [ ] **步骤 2：编写确认入库持久化特征测试**

继续在同一测试类中加入：

```python
    async def test_confirm_persists_reviewed_fields(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(bind=engine)
        db = session_factory()
        payload = ConfirmRequest(
            text="已人工校对的题干",
            question_type="解答题",
            difficulty=4,
            knowledge_points=["相似三角形"],
            has_diagram=True,
            raw_ocr_text="原始 OCR",
            final_answer="最终答案",
            solution_text="人工解析",
            key_insight="构造相似",
            knowmap_nodes=["node-1"],
            analysis_source="ocr",
            analysis_confidence=65,
            needs_human_review=False,
        )

        try:
            with patch(
                "backend.routers.upload._get_llm_config",
                return_value=(False, None),
            ):
                result = await confirm_question(payload, request=None, db=db)

            saved = db.query(Question).filter(Question.id == result["question_id"]).one()
            self.assertEqual(saved.text, "已人工校对的题干")
            self.assertEqual(saved.raw_ocr_text, "原始 OCR")
            self.assertEqual(saved.analysis_source, "ocr")
            self.assertEqual(saved.analysis_confidence, 65)
            self.assertEqual(json.loads(saved.knowledge_points), ["相似三角形"])
            self.assertEqual(json.loads(saved.knowmap_nodes), ["node-1"])
            self.assertEqual(saved.final_answer, "最终答案")
            self.assertEqual(saved.review_status, "complete")
            self.assertFalse(saved.needs_human_review)
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 3：运行契约测试**

运行：

```powershell
python -m unittest backend.tests.test_upload_contract -v
```

预期：3 个测试全部通过。若有失败，将失败记录为基线问题，不修改生产代码；先确认测试是否准确表达当前 v1.1 设计。

- [ ] **步骤 4：运行后端完整测试**

运行：

```powershell
python -m unittest discover -s backend/tests -p "test_*.py"
```

预期：原有 4 个测试加新增 10 个测试，共 14 个测试通过。

- [ ] **步骤 5：提交契约测试**

```powershell
git add backend/tests/test_upload_contract.py
git commit -m "test(入库): 锁定多图分析与确认契约"
```

---

### 任务 4：建立验收报告骨架

**文件：**

- 创建：`docs/quality/real-question-baseline-2026-06-27.md`
- 创建：`docs/quality/cases/RQ-01.md`
- 创建：`docs/quality/cases/RQ-02.md`
- 创建：`docs/quality/cases/RQ-03.md`
- 创建：`docs/quality/cases/RQ-04.md`
- 创建：`docs/quality/cases/RQ-05.md`

- [ ] **步骤 1：创建总览文档**

创建 `docs/quality/real-question-baseline-2026-06-27.md`，写入：

```markdown
# 真实复杂题验收基线

> 执行状态：not_run
> 执行日期：2026-06-27
> 设计规格：`docs/superpowers/specs/2026-06-27-real-question-acceptance-baseline-design.md`

## 环境

| 项目 | 记录 |
|------|------|
| Git 基线 | 45fed0c |
| OCR | not_run |
| 文本模型 | DeepSeek / deepseek-chat |
| 前端 | http://127.0.0.1:5173/ |
| 后端 | http://127.0.0.1:8000/ |

## 结果总览

| 案例 | 状态 | 得分 | P0 | P1 | P2 | question_id | 可进入下一阶段 |
|------|------|------|----|----|----|-------------|----------------|
| RQ-01 | not_run | 0 | 0 | 0 | 0 | null | 否 |
| RQ-02 | not_run | 0 | 0 | 0 | 0 | null | 否 |
| RQ-03 | not_run | 0 | 0 | 0 | 0 | null | 否 |
| RQ-04 | not_run | 0 | 0 | 0 | 0 | null | 否 |
| RQ-05 | not_run | 0 | 0 | 0 | 0 | null | 否 |

## 共因排序

基线尚未执行，因此没有已确认共因。

## 首个修复包

基线尚未执行，因此没有选定修复包。
```

- [ ] **步骤 2：创建逐题报告**

每个 `docs/quality/cases/RQ-0N.md` 使用以下固定结构，并将标题替换为案例清单中的准确题名：

```markdown
# RQ-0N：准确题名

> 状态：not_run
> question_id：null
> session_id：null

## 输入

- 图片顺序：以 `data/acceptance/real-question-cases.json` 为准。
- 对照材料：以案例清单中的 `reference` 为准。

## 自动分析原始结果

- 来源：not_run
- 置信度：0
- OCR 文本：not_run
- 结构化题干：not_run
- 题型：not_run
- 知识点：not_run
- 题眼：not_run
- 是否含图：not_run

## 人工校对

- 修改字段数：0
- 修改内容：not_run
- 数学冲突：not_run

## 导学执行

- 正确回答分支：not_run
- 错误回答分支：not_run
- 提示分支：not_run
- 连续错误分支：not_run
- 完成状态：false
- 诊断摘要：not_run

## 评分

| 维度 | 分值 |
|------|------|
| multi_image | 0 |
| text_formula | 0 |
| diagram_semantics | 0 |
| structured_fields | 0 |
| solution_consistency | 0 |
| tutor_quality | 0 |
| diagnostic_quality | 0 |

## 问题

当前没有记录问题，因为案例尚未执行。

## 结论

- 加权总分：0
- 存在 P0：false
- 可进入下一阶段：false
```

准确标题：

- `RQ-01：几何变换与动点问题综合探究`
- `RQ-02：二次函数综合探究`
- `RQ-03：四边形折叠中的相似与隐圆最值`
- `RQ-04：K 型全等模型在一次函数中的综合探究`
- `RQ-05：圆的切线判定与阴影面积`

- [ ] **步骤 3：检查报告文件齐全**

运行：

```powershell
Get-ChildItem docs\quality\cases\RQ-*.md | Select-Object Name
```

预期：恰好列出 `RQ-01.md` 至 `RQ-05.md`。

- [ ] **步骤 4：提交报告骨架**

```powershell
git add docs/quality
git commit -m "docs(验收): 建立真实题基线报告骨架"
```

---

### 任务 5：执行运行环境预检

**文件：**

- 修改：`docs/quality/real-question-baseline-2026-06-27.md`

- [ ] **步骤 1：启动后端**

在独立终端运行：

```powershell
cd D:\Sven\maths
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

等待日志出现 `Startup complete`。PaddleOCR 首次初始化可能需要 30 至 120 秒。

- [ ] **步骤 2：验证后端和 OCR**

运行：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ocr
```

预期：

- `/health` 返回 `status: ok`。
- OCR 返回 `status: ready`。
- 后端启动日志没有 `PaddleOCR unavailable` 或模型加载异常。

若 OCR 初始化失败：

1. 在总览环境表记录完整错误。
2. 将自动入库路径标记为 P0。
3. 后续案例仍使用人工输入兜底完成导学链路。
4. 不在本任务中重装依赖或改 OCR 代码。

- [ ] **步骤 3：验证文本模型连接**

在设置页使用现有 DeepSeek 配置点击“测试连接”，同时在 Chrome DevTools Network 面板检查：

- 请求：`POST /api/v1/settings/models/test`
- HTTP 状态：200
- 响应：`status: ok`
- 请求和控制台不显示 API Key 明文

若连接失败，将错误记录为环境问题；OCR 原始识别仍继续执行，AI 结构化和自动解答标记为阻断。

- [ ] **步骤 4：启动前端**

在独立终端运行：

```powershell
cd D:\Sven\maths\frontend
npm run dev
```

打开 `http://127.0.0.1:5173/`。

- [ ] **步骤 5：填写总览环境表**

将 OCR 实际状态、模型测试结果、浏览器版本和 Git 当前提交写入总览文档，并把总览状态从 `not_run` 改为 `running`。

- [ ] **步骤 6：提交环境预检结果**

```powershell
git add docs/quality/real-question-baseline-2026-06-27.md
git commit -m "docs(验收): 记录真实题运行环境"
```

---

### 任务 6：执行 RQ-01 与 RQ-02

**文件：**

- 修改：`docs/quality/cases/RQ-01.md`
- 修改：`docs/quality/cases/RQ-02.md`
- 修改：`docs/quality/real-question-baseline-2026-06-27.md`

- [ ] **步骤 1：执行 RQ-01 自动分析**

在入库页按清单顺序一次选择 RQ-01 的 3 张图片。点击“解析入库”，在 Chrome DevTools 中保存以下证据到 `RQ-01.md`：

- `/api/v1/questions/analyze` 的 HTTP 状态。
- 请求中 3 个 `image` 字段的文件名顺序。
- 完整响应中的 `source`、`raw_ocr_text`、`text`、`confidence`、`knowledge_points`、`key_insight` 和 `has_diagram`。
- 控制台错误。

- [ ] **步骤 2：校对并确认 RQ-01**

逐项对照原图和解构稿，记录所有修改。必须检查：

- `0 < t < 10`、`5 < t < 10`、`0 < t < 5` 三个区间。
- 点 `P`、`Q` 的运动方向和速度。
- 图 1、图 2、备用图的用途。
- 三个问题是否完整。

确认入库后，从响应记录 `question_id`。

- [ ] **步骤 3：执行 RQ-01 导学分支**

进入导学后按顺序执行：

1. 对当前步骤输入一次明显错误回答“把所有已知长度直接相加”。
2. 点击一次“提示”。
3. 再输入两次“不知道”，触发连续错误分支。
4. 对后续步骤使用页面当前问题对应的正确数学结论完成会话。
5. 记录 `session_id`、诊断摘要、复习计划是否生成。

如果当前题只有一个导学步骤，连续错误会直接完成会话；如实记录，不重复创建会话。

- [ ] **步骤 4：评分 RQ-01**

根据证据填写 7 个维度的 0/1/2 分和全部问题。用以下命令计算门禁：

```powershell
@'
from tools.acceptance_scoring import evaluate_case

scores = {
    "multi_image": 0,
    "text_formula": 0,
    "diagram_semantics": 0,
    "structured_fields": 0,
    "solution_consistency": 0,
    "tutor_quality": 0,
    "diagnostic_quality": 0,
}
issues = []
print(evaluate_case(scores, issues, tutor_completed=False))
'@ | python -
```

执行时把字典中的 7 个分值、`issues` 和 `tutor_completed` 替换为报告中已经确认的实际值，并把输出写回 `RQ-01.md`。

- [ ] **步骤 5：执行并评分 RQ-02**

按 RQ-01 相同流程处理 RQ-02 的 4 张图片。额外核对：

- `y = x^2 - 2kx + k - 1`。
- 平移量 `1/2` 和 `1`。
- `A(x_1, 0)`、`B(x_2, 0)` 及 `x_1 < x_2`。
- 一次函数中的 `5/4`。
- 题干页和答案页是否被正确区分。

将实际结果写入 `RQ-02.md` 和总览表。

- [ ] **步骤 6：提交前两题结果**

```powershell
git add docs/quality/cases/RQ-01.md docs/quality/cases/RQ-02.md docs/quality/real-question-baseline-2026-06-27.md
git commit -m "test(真实题): 完成动点与二次函数基线"
```

---

### 任务 7：执行 RQ-03 与 RQ-04

**文件：**

- 修改：`docs/quality/cases/RQ-03.md`
- 修改：`docs/quality/cases/RQ-04.md`
- 修改：`docs/quality/real-question-baseline-2026-06-27.md`

- [ ] **步骤 1：执行并评分 RQ-03**

按任务 6 的分析、校对、导学和评分流程处理 RQ-03 的 3 张图片。额外核对：

- `A'`、`D'` 的撇号必须保留。
- 图 1 至图 4 与对应小问不能错配。
- “沿 BE 翻折”的对应点关系。
- `D'` 落在 `BC` 与 `A'` 落在 `BC` 是两个不同情形。
- `CP` 最小值问题没有被误写为面积问题。

- [ ] **步骤 2：执行并评分 RQ-04**

按相同流程处理 RQ-04 的 2 张图片。额外核对：

- `l_1: y = 2x + 4` 与 `AB: y = 2x + 8` 不得混淆。
- 第二象限约束。
- 顺时针旋转 `45°`。
- K 型全等的垂线关系。
- 正方形存在性需要分类讨论。

- [ ] **步骤 3：更新总览**

将 RQ-03、RQ-04 的状态、得分、问题数量、`question_id` 和门禁结果写入总览。

- [ ] **步骤 4：提交中间两题结果**

```powershell
git add docs/quality/cases/RQ-03.md docs/quality/cases/RQ-04.md docs/quality/real-question-baseline-2026-06-27.md
git commit -m "test(真实题): 完成折叠与全等模型基线"
```

---

### 任务 8：执行 RQ-05 错误标答压力测试

**文件：**

- 修改：`docs/quality/cases/RQ-05.md`
- 修改：`docs/quality/real-question-baseline-2026-06-27.md`

- [ ] **步骤 1：执行 RQ-05 自动分析与校对**

按清单顺序上传 3 张图片，记录分析响应。重点检查：

- `AB` 是直径。
- `AD` 是 `∠BAC` 的平分线。
- `CF ∥ AE`。
- `OD ⟂ AB`。
- 题目要求证明切线并计算阴影面积。

- [ ] **步骤 2：执行数学自洽性检查**

对比原图、原答案和解构稿，明确记录：

- 系统是否直接照搬原标答。
- 系统是否错误使用圆周角定理。
- 切线证明与阴影面积所需角度是否相互矛盾。
- 系统是否主动提示“需要人工复核”。

如果系统输出确定性错误结论，记录为 P0。仅仅与原标答一致不能判定为正确。

- [ ] **步骤 3：执行导学并评分**

执行错误、提示、连续错误和完成分支。检查导学是否把矛盾条件继续当成正确前提。填写全部评分和门禁结果。

- [ ] **步骤 4：更新总览并提交**

```powershell
git add docs/quality/cases/RQ-05.md docs/quality/real-question-baseline-2026-06-27.md
git commit -m "test(真实题): 完成错误标答压力测试"
```

---

### 任务 9：汇总共因并选择首个修复包

**文件：**

- 修改：`docs/quality/real-question-baseline-2026-06-27.md`
- 修改：`docs/PROJECT_STATUS.md`

- [ ] **步骤 1：核对 5 题完成度**

运行：

```powershell
rg -n "状态：not_run|question_id：null|session_id：null" docs/quality/cases
```

预期：没有输出。若某题被阻断，报告中必须使用 `blocked` 和完整阻断原因，不能保留 `not_run` 或 `null`。

- [ ] **步骤 2：按共因聚合问题**

在总览中按以下固定顺序整理：

1. 跨多题出现的 P0。
2. 单题 P0。
3. 跨多题出现的 P1。
4. 单题 P1。
5. P2。

每个共因必须列出受影响案例、复现入口和相关代码文件。

- [ ] **步骤 3：选择一个修复包**

严格应用设计中的选择规则：

- 优先跨多题共同 P0。
- P0 根因不同则优先入库阶段。
- 没有 P0 才选择影响最多题目的 P1。
- 不把多个根因合并成一个修复包。

在总览“首个修复包”中写明：

- 根因。
- 受影响案例。
- 为什么优先。
- 预计修改文件。
- 回归测试范围。

- [ ] **步骤 4：更新项目状态**

在 `docs/PROJECT_STATUS.md` 中：

- 将“真实复杂含图题尚未经过端到端验证”替换为本次实际结论。
- 更新 Phase B、Phase C 的真实验收状态。
- 记录 5 个 `question_id` 和会话完成数量。
- 将恢复开发入口改为本次选定的首个修复包。

- [ ] **步骤 5：提交汇总**

```powershell
git add docs/quality/real-question-baseline-2026-06-27.md docs/PROJECT_STATUS.md
git commit -m "docs(验收): 汇总真实复杂题基线结论"
```

---

### 任务 10：最终验证与交接

**文件：**

- 修改：`docs/quality/real-question-baseline-2026-06-27.md`（仅在验证结果需要补充时）

- [ ] **步骤 1：运行全部后端测试**

```powershell
python -m unittest discover -s backend/tests -p "test_*.py"
python -m compileall -q backend tools
```

预期：14 个测试通过，编译检查退出码为 0。

- [ ] **步骤 2：运行全部前端检查**

```powershell
node --test frontend/src/components/knowmapPicker.test.mjs
cd frontend
npx tsc --noEmit
npm run build
```

预期：

- Node 测试 5 个通过。
- TypeScript 检查退出码为 0。
- Vite 构建成功。

- [ ] **步骤 3：执行 Chrome DevTools 最终检查**

在桌面端 `1440 × 900` 和移动端 `390 × 844` 检查：

- 入库页可看到全部已选择图片。
- 长题干和公式不溢出。
- 校对控件与确认按钮状态正确。
- 导学完成页显示诊断摘要。
- Console 没有新增错误。
- Network 中 analyze、confirm、session、message 请求均成功或已在报告中记录失败原因。

- [ ] **步骤 4：验证文档和 Git**

```powershell
rg -n "not_run|基线尚未执行" docs/quality
git diff --check
git status --short
git log --oneline -10
```

预期：

- `docs/quality` 中没有未执行状态。
- `git diff --check` 无输出。
- `git status --short` 无输出。
- 最近提交包含案例清单、评分、契约测试、5 题结果和汇总结论。

- [ ] **步骤 5：停止开发服务**

停止本轮启动的前后端进程，确认端口释放：

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in 5173, 8000 }
```

预期：没有输出。

- [ ] **步骤 6：报告交接结果**

向用户报告：

- 5 题执行数量与通过数量。
- P0/P1/P2 数量。
- 得分最低的案例。
- 选定的首个修复包。
- 测试和 Chrome DevTools 验证证据。
- 下一步只进入选定修复包，不同时推进其他阶段。
