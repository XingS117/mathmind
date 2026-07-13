import json
import logging
import time
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from backend.database import get_db, SessionLocal
from backend.models.question import Question
from backend.models.settings import UserSettings
from backend.schemas.api_schemas import QuestionAnalysisResponse, QuestionConfirmResponse
from backend.services.auth_service import get_user_id
from backend.services.llm_service import call_llm_with_config
from backend.services.ocr_service import ocr_image
from backend.services.knowmap_matcher import suggest_nodes
from backend.services.knowmap_service import get_tree
from backend.services.operations_service import record_runtime_event

logger = logging.getLogger(__name__)
router = APIRouter(tags=["upload"])


def _record_vision_runtime(config: dict, outcome: str, started: float, error_code: str | None = None) -> None:
    db = SessionLocal()
    try:
        record_runtime_event(
            db, feature="ocr", engine_kind="vision", provider=config.get("model_provider", ""),
            model_name=config.get("model_name", ""), outcome=outcome,
            duration_ms=round((time.monotonic() - started) * 1000), error_code=error_code,
        )
    except Exception:
        logger.warning("Failed to record vision OCR runtime event", exc_info=True)
    finally:
        db.close()


class ConfirmRequest(BaseModel):
    text: str
    question_type: str = "计算题"
    difficulty: int = 2
    knowledge_points: List[str] = []
    has_diagram: bool = False
    raw_ocr_text: str = ""
    final_answer: str = ""
    solution_text: str = ""
    key_insight: str = ""
    knowmap_nodes: List[str] = []
    analysis_source: str = "manual"
    analysis_confidence: int = 0
    needs_human_review: bool = False


ANALYZE_PROMPT = """你是一名深耕初高中数学教学的教研员。

请分析以下 OCR 识别出的数学题文本，输出结构化的 JSON 数据。

要求：
1. 用标准文字和 LaTeX 公式准确复原题目
2. 明确指出核心考点（对应课标知识点）
3. 指出解题突破口（题眼）
4. 判断是否需要 SVG 几何示意图

输出严格 JSON 格式（只输出 JSON，不要其他文本）：
{
  "valid": true,
  "text": "完整题目文本（含 LaTeX 公式）",
  "question_type": "选择题|填空题|计算题|解答题|证明题|几何题",
  "knowledge_points": ["知识点1", "知识点2"],
  "difficulty": 1,
  "has_diagram": false,
  "key_insight": "解题题眼（1-2句）"
}

若 OCR 文本不包含有效数学题，或无法识别为题目，则输出：
{"valid": false, "error": "未识别到有效数学题目", "suggestion": "请确认图片清晰、包含完整的印刷体数学题"}
"""

SOLVE_PROMPT = """你是初高中数学教研员，正在为学生做**逐步讲解**。

严格按以下流程解题，然后输出 JSON：

1. **复述条件**：把题目已知条件用一句话复述，标明求什么。若题干存在矛盾或
   缺失关键条件，直接把 `confidence` 设为 `"low"` 并在 `uncertain_points`
   中说明，不要强行编答案。
2. **分步骤**：每步给出：
   - `description`：这一步做什么（简短，不含答案）；
   - `basis`：这一步用到的定理/公式/依据；
   - `latex`：涉及的公式；
   - `result`：这一步得到的中间结论。
   步骤要覆盖从已知到最终答案的完整推理，最少 3 步。
3. **给出 final_answer**：并用一句话说明"如何验证 final_answer 满足题干"。
4. **自检**：把答案代回题干条件，检查是否全部满足。若发现矛盾，把
   `confidence` 设为 `"low"` 并在 `uncertain_points` 中说明。

要求：
- 不允许在 `description` 里直接写出 `result`。
- 不允许步骤间出现前后矛盾（例如第2步得到 x=1，第3步却使用 x=2）。
- 化简所有能化简的表达式（例如 `\\sqrt{4k^2-4k+2}` 应写成 `\\sqrt{(2k-1)^2+1}`）。
- **只输出 JSON**，不要有前后文字。

输出格式：
```json
{
  "steps": [
    {"step_number": 1, "description": "…", "basis": "…", "latex": "…", "result": "…"}
  ],
  "final_answer": "最终答案",
  "verification": "把最终答案代回题干后，如何验证条件全部满足",
  "method": "解法名称",
  "common_mistakes": ["常见错误1"],
  "confidence": "high" | "medium" | "low",
  "uncertain_points": ["若有把握不准之处列在这里"]
}
```
"""


def _analysis_response(**kwargs) -> dict:
    base = QuestionAnalysisResponse(success=True).model_dump()
    base.update(kwargs)
    return base


def _strip_code_fence(text: str) -> str:
    """Some LLMs wrap JSON output in ```json fences. Strip them so
    ``json.loads`` doesn't fail on otherwise valid payloads.
    """
    if not text:
        return text
    t = text.strip()
    if t.startswith("```"):
        # Drop the opening fence line and the closing fence.
        first_newline = t.find("\n")
        if first_newline != -1:
            t = t[first_newline + 1 :]
        if t.endswith("```"):
            t = t[: -3]
    return t.strip()


def _get_llm_config(uid: str) -> tuple[bool, dict | None]:
    """Resolve LLM config with the following precedence:

    1. ``MATHMIND_LLM_API_KEY`` (or provider-specific env below) — always wins
       so production deployments do not have to store keys in the SQLite
       ``UserSettings`` table.
    2. Current user's ``UserSettings`` row.
    3. ``u_admin``'s ``UserSettings`` row (fallback for the default user).

    Provider-specific env fallbacks (used only when
    ``MATHMIND_LLM_API_KEY`` is not set): ``DEEPSEEK_API_KEY`` +
    ``MATHMIND_LLM_PROVIDER``/``MATHMIND_LLM_MODEL``/``MATHMIND_LLM_BASE_URL``.
    """

    import os as _os
    from backend.database import SessionLocal

    env_key = _os.getenv("MATHMIND_LLM_API_KEY") or _os.getenv("DEEPSEEK_API_KEY")
    if env_key:
        provider = _os.getenv("MATHMIND_LLM_PROVIDER", "deepseek")
        model = _os.getenv("MATHMIND_LLM_MODEL", "deepseek-chat")
        base_url = _os.getenv("MATHMIND_LLM_BASE_URL", "")
        return True, {
            "model_provider": provider,
            "api_key": env_key,
            "model_name": model,
            "base_url": base_url,
        }

    db = SessionLocal()
    try:
        config_rec = db.query(UserSettings).filter(UserSettings.user_id == uid).first()
        if not config_rec or not config_rec.api_key or config_rec.model_provider == "mock":
            admin_rec = db.query(UserSettings).filter(UserSettings.user_id == "u_admin").first()
            if admin_rec and admin_rec.api_key and admin_rec.model_provider != "mock":
                config_rec = admin_rec
        has_llm = bool(config_rec and config_rec.api_key and config_rec.model_provider != "mock")
        if not has_llm:
            return False, None
        return True, {
            "model_provider": config_rec.model_provider,
            "api_key": config_rec.api_key,
            "model_name": config_rec.model_name,
            "base_url": config_rec.base_url or "",
        }
    finally:
        db.close()


@router.post("/questions/analyze", response_model=QuestionAnalysisResponse)
async def analyze_question(images: List[UploadFile] = File(alias="image"), request: Request = None):
    if not images:
        return JSONResponse(
            {"success": False, "error": "请选择至少一张图片", "suggestion": "点击或拖拽图片到上传区域"},
            status_code=400,
        )

    uid = get_user_id(request) if request else "u_default"
    has_llm, llm_config = _get_llm_config(uid)
    raw_parts: list[str] = []
    source = "ocr"

    for idx, image in enumerate(images, start=1):
        img_bytes = await image.read()
        part = ""
        try:
            part = await ocr_image(img_bytes)
            logger.info(f"OCR result[{idx}]: " + ("empty" if not part else part[:60] + "..."))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"OCR failed[{idx}]: {exc}")
            part = ""

        if not part and llm_config:
            provider = llm_config.get("model_provider", "")
            if provider in ("openai", "gemini", "qwen"):
                started = time.monotonic()
                vision_outcome = "success"
                vision_error = None
                try:
                    from backend.services.vision_ocr_service import ocr_with_vision_llm
                    vision_text = await ocr_with_vision_llm(img_bytes, llm_config)
                    if vision_text:
                        part = vision_text
                        source = "vision"
                        logger.info(f"Vision OCR result: {vision_text[:60]}...")
                except Exception as e:
                    vision_outcome = "error"
                    vision_error = type(e).__name__
                    logger.warning(f"Vision OCR failed: {e}")
                finally:
                    _record_vision_runtime(llm_config, vision_outcome, started, vision_error)

        if part:
            raw_parts.append(f"--- 第 {idx} 张 ---\n{part}" if len(images) > 1 else part)

    raw_text = "\n\n".join(raw_parts).strip()
    if not raw_text:
        return _analysis_response(
            source="manual_input",
            confidence=0,
            needs_human_review=True,
            suggestion="未能自动识别文字，请手动输入题目内容后入库。",
        )

    if not has_llm or not llm_config:
        return _analysis_response(
            source=source,
            text=raw_text,
            raw_ocr_text=raw_text,
            confidence=45,
            needs_human_review=True,
            suggestion="已识别出文字，但未配置 AI 模型，请人工校对题干、知识点和答案。",
        )

    raw = await call_llm_with_config(ANALYZE_PROMPT + "\n\nOCR 文本：\n" + raw_text, llm_config)
    if not raw:
        return _analysis_response(
            source=source,
            text=raw_text,
            raw_ocr_text=raw_text,
            confidence=45,
            needs_human_review=True,
            suggestion="AI 分析失败，已保留 OCR 文本，请人工校对后入库。",
        )

    try:
        data = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError:
        return _analysis_response(
            source=source,
            text=raw_text,
            raw_ocr_text=raw_text,
            confidence=40,
            needs_human_review=True,
            suggestion="AI 返回格式异常，已保留 OCR 文本，请人工校对后入库。",
        )

    if data.get("valid") is False:
        return JSONResponse(
            {
                "success": False,
                "error": data.get("error", "未识别到有效题目"),
                "suggestion": data.get("suggestion", "请确认图片内容为完整的数学题目"),
            },
            status_code=200,
        )

    return _analysis_response(
        source=source,
        text=data.get("text", raw_text),
        question_type=data.get("question_type", "计算题"),
        knowledge_points=data.get("knowledge_points", []),
        suggested_nodes=suggest_nodes(data.get("knowledge_points", []), get_tree("")),
        difficulty=data.get("difficulty", 2),
        has_diagram=data.get("has_diagram", False),
        key_insight=data.get("key_insight", ""),
        raw_ocr_text=raw_text,
        confidence=80,
        needs_human_review=True,
    )


@router.post("/questions/confirm", response_model=QuestionConfirmResponse)
async def confirm_question(data: ConfirmRequest, request: Request = None, db: DBSession = Depends(get_db)):
    uid = get_user_id(request) if request else "u_default"
    qid = f"q_{uuid.uuid4().hex[:12]}"
    _, llm_config = _get_llm_config(uid)

    # 兜底: 若前端没勾图谱节点但有知识点, 用 matcher 再挂一次 (P1-UX-KP-01).
    # 这样即便用户跳过图谱区块直接入库, 后端也能给这道题绑上合适的节点.
    if not data.knowmap_nodes and data.knowledge_points:
        try:
            data.knowmap_nodes = suggest_nodes(
                data.knowledge_points, get_tree(""), limit=3
            )
            if data.knowmap_nodes:
                logger.info(
                    f"confirm auto-bound {len(data.knowmap_nodes)} nodes for {qid}: {data.knowmap_nodes}"
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"confirm auto-bind failed: {exc}")

    steps = []
    final_answer = data.final_answer or ""
    method = ""
    common_mistakes = []
    teachable = []
    verification = ""
    llm_confidence = "unknown"
    uncertain_points: list[str] = []

    if llm_config and data.text:
        raw = await call_llm_with_config(SOLVE_PROMPT + "\n\n题干：\n" + data.text, llm_config)
        if raw:
            try:
                solve = json.loads(_strip_code_fence(raw))
                steps = solve.get("steps", [])
                final_answer = final_answer or solve.get("final_answer", "")
                method = solve.get("method", "")
                common_mistakes = solve.get("common_mistakes", [])
                verification = solve.get("verification", "") or ""
                llm_confidence = str(solve.get("confidence") or "unknown").lower()
                uncertain_points = list(solve.get("uncertain_points") or [])
                for s in steps:
                    step_no = s.get("step_number", 1)
                    description = str(s.get("description") or "").strip()
                    basis = str(s.get("basis") or "").strip()
                    result_val = str(s.get("result") or "").strip()
                    guiding = description
                    if basis and basis not in guiding:
                        guiding = f"{description}（依据：{basis}）" if description else basis
                    teachable.append({
                        "step_number": step_no,
                        "title": f"第{step_no}步",
                        "guiding_question": guiding,
                        "expected_answer": result_val,
                        "correct_response": "正确！继续。",
                        "wrong_response": "再想想。",
                        "hint": description or basis or "回到已知条件想一想。",
                        "stuck_response": result_val,
                        "basis": basis,
                    })
            except Exception:
                pass

    needs_review_final = data.needs_human_review or llm_confidence == "low" or bool(uncertain_points)

    if not teachable and data.text:
        teachable.append({
            "step_number": 1,
            "title": "理解题意",
            "guiding_question": data.key_insight or "这道题的突破口是什么？",
            "expected_answer": final_answer,
            "correct_response": "很好，继续保持这个思路。",
            "wrong_response": "先回到题干，找出已知条件和要求。",
            "hint": data.key_insight or "先标出题目要求和关键条件。",
            "stuck_response": final_answer or data.solution_text or "先把题干中的条件逐条整理。",
        })

    q = Question(
        id=qid,
        user_id=uid,
        source="photo",
        source_label="好题",
        raw_ocr_text=data.raw_ocr_text or "",
        analysis_source=data.analysis_source,
        analysis_confidence=data.analysis_confidence,
        review_status="complete",
        needs_human_review=data.needs_human_review,
        text=data.text or "",
        question_type=data.question_type,
        difficulty=data.difficulty,
        knowledge_points=json.dumps(data.knowledge_points),
        knowmap_nodes=json.dumps(data.knowmap_nodes),
        has_diagram=data.has_diagram,
        final_answer=final_answer,
        solution_json=json.dumps({
            "steps": steps,
            "final_answer": final_answer,
            "method": method,
            "common_mistakes": common_mistakes,
            "manual_solution": data.solution_text,
            "verification": verification,
            "confidence": llm_confidence,
            "uncertain_points": uncertain_points,
        }),
        teaching_json=json.dumps({
            "teachable_steps": teachable,
            "prerequisites": [],
            "key_insight": data.key_insight,
            "uncertain_points": uncertain_points,
            "solution_confidence": llm_confidence,
        }),
        status="complete",
    )
    # Preserve the LLM self-check flag by promoting it into
    # ``needs_human_review`` so the frontend can prompt the user to
    # spot-check questionable auto-solutions.
    q.needs_human_review = needs_review_final
    db.add(q)
    db.commit()
    return {
        "question_id": qid,
        "status": "complete",
        "review_status": "complete",
        "text": (data.text or "")[:60],
    }


@router.get("/questions/{qid}/status")
def question_status(qid: str, request: Request = None, db: DBSession = Depends(get_db)):
    q = db.query(Question).filter(Question.id == qid).first()
    if not q:
        raise HTTPException(404, "Question not found")
    return {
        "id": q.id,
        "status": q.status,
        "review_status": q.review_status,
        "question_type": q.question_type,
    }
