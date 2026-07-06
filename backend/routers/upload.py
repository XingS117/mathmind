import json
import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from backend.database import get_db
from backend.models.question import Question
from backend.models.settings import UserSettings
from backend.schemas.api_schemas import QuestionAnalysisResponse, QuestionConfirmResponse
from backend.services.auth_service import get_user_id
from backend.services.llm_service import call_llm_with_config
from backend.services.ocr_service import ocr_image

logger = logging.getLogger(__name__)
router = APIRouter(tags=["upload"])


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

SOLVE_PROMPT = """解以下数学题，输出严格 JSON 格式：
{
  "steps": [{"step_number": 1, "description": "步骤说明", "latex": "公式", "result": "结果"}],
  "final_answer": "最终答案",
  "method": "解法名称",
  "common_mistakes": ["常见错误1"]
}
"""


def _analysis_response(**kwargs) -> dict:
    base = QuestionAnalysisResponse(success=True).model_dump()
    base.update(kwargs)
    return base


def _get_llm_config(uid: str) -> tuple[bool, dict | None]:
    from backend.database import SessionLocal

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
                try:
                    from backend.services.vision_ocr_service import ocr_with_vision_llm

                    vision_text = await ocr_with_vision_llm(img_bytes, llm_config)
                    if vision_text:
                        part = vision_text
                        source = "vision"
                        logger.info(f"Vision OCR result: {vision_text[:60]}...")
                except Exception as e:
                    logger.warning(f"Vision OCR failed: {e}")

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
        data = json.loads(raw)
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

    steps = []
    final_answer = data.final_answer or ""
    method = ""
    common_mistakes = []
    teachable = []

    if llm_config and data.text:
        raw = await call_llm_with_config(SOLVE_PROMPT + "\n\n" + data.text, llm_config)
        if raw:
            try:
                solve = json.loads(raw)
                steps = solve.get("steps", [])
                final_answer = final_answer or solve.get("final_answer", "")
                method = solve.get("method", "")
                common_mistakes = solve.get("common_mistakes", [])
                for s in steps:
                    teachable.append({
                        "step_number": s.get("step_number", 1),
                        "title": f"第{s.get('step_number', 1)}步",
                        "guiding_question": s.get("description", ""),
                        "expected_answer": s.get("result", ""),
                        "correct_response": "正确！继续。",
                        "wrong_response": "再想想，提示：" + s.get("description", ""),
                        "hint": s.get("description", ""),
                        "stuck_response": s.get("result", ""),
                    })
            except Exception:
                pass

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
        }),
        teaching_json=json.dumps({
            "teachable_steps": teachable,
            "prerequisites": [],
            "key_insight": data.key_insight,
        }),
        status="complete",
    )
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
