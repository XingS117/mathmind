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

            saved = (
                db.query(Question).filter(Question.id == result["question_id"]).one()
            )
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
