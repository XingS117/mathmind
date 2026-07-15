"""Pure-Python tests for backend.services.ocr_service result parsing.

These tests never import PaddleOCR; they exercise the defensive text
extractor so it survives both the legacy ``ocr()`` shape and the 3.x
``predict()`` dict shape without a working Paddle install.
"""

import unittest

from backend.services import ocr_service


class ExtractTextsTest(unittest.TestCase):
    def test_legacy_ocr_shape_returns_lines_in_order(self):
        legacy = [[
            [[[0, 0], [1, 0], [1, 1], [0, 1]], ("第一行", 0.99)],
            [[[0, 1], [1, 1], [1, 2], [0, 2]], ("第二行", 0.87)],
        ]]
        self.assertEqual(
            ocr_service._extract_texts(legacy),
            ["第一行", "第二行"],
        )

    def test_predict_dict_shape_with_rec_texts(self):
        predict_result = [
            {
                "rec_texts": ["解 方程", "得 x=1"],
                "rec_scores": [0.98, 0.95],
            }
        ]
        self.assertEqual(
            ocr_service._extract_texts(predict_result),
            ["解 方程", "得 x=1"],
        )

    def test_predict_dict_shape_wrapped_in_res(self):
        wrapped = {"res": [{"rec_texts": ["A", "B"]}]}
        self.assertEqual(ocr_service._extract_texts(wrapped), ["A", "B"])

    def test_none_and_empty_never_raise(self):
        self.assertEqual(ocr_service._extract_texts(None), [])
        self.assertEqual(ocr_service._extract_texts([]), [])
        self.assertEqual(ocr_service._extract_texts([[None]]), [])

    def test_skips_empty_and_whitespace_lines(self):
        predict_result = [{"rec_texts": ["有效", "", "   ", "另一个"]}]
        self.assertEqual(
            ocr_service._extract_texts(predict_result),
            ["有效", "另一个"],
        )

    def test_ignores_unexpected_shapes_without_raising(self):
        self.assertEqual(ocr_service._extract_texts(42), [])
        self.assertEqual(ocr_service._extract_texts("string"), [])
        self.assertEqual(
            ocr_service._extract_texts([{"unrelated": "field"}]),
            [],
        )


if __name__ == "__main__":
    unittest.main()