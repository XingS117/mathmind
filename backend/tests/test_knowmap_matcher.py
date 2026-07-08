"""Regression tests for AI-suggested knowmap nodes (P1-UX-KP-01).

These pin the mapping from free-text LLM labels like ``"等腰三角形的性质"``
to knowmap node IDs so upload校对页 can offer one-click suggestions.
"""

import unittest

from backend.services.knowmap_matcher import suggest_nodes


NODES = [
    {"id": "bx1_c1", "name": "第1章 集合", "level": 2, "parent_id": "bx1"},
    {"id": "bx1_c1_s1", "name": "1.1 集合的概念", "level": 3, "parent_id": "bx1_c1"},
    {"id": "cz_bs2_c5", "name": "第5章 三角形", "level": 2, "parent_id": "cz_bs2"},
    {"id": "cz_bs2_c5_s1", "name": "5.1 等腰三角形", "level": 3, "parent_id": "cz_bs2_c5"},
    {"id": "cz_bs2_c5_s2", "name": "5.2 全等三角形", "level": 3, "parent_id": "cz_bs2_c5"},
    {"id": "cz_bs2_c5_s3", "name": "5.3 三角形的中位线", "level": 3, "parent_id": "cz_bs2_c5"},
    {"id": "bx2_c3_s2", "name": "3.2 二次函数的图像与性质", "level": 3, "parent_id": "bx2_c3"},
    {"id": "bx1", "name": "必修一", "level": 1, "parent_id": None},
]


class SuggestNodesTest(unittest.TestCase):
    def test_matches_exact_and_suffix_variants(self):
        got = suggest_nodes(
            ["等腰三角形的性质", "三角形中位线定理", "全等三角形的判定与性质"],
            NODES,
        )
        # All three labels are about triangles; matcher should find the
        # 三角形 leaves and/or its parent chapter, but must not surface
        # unrelated 函数/集合/椭圆 nodes.
        for nid in got:
            self.assertTrue(
                nid.startswith("cz_bs2_c5") or nid == "cz_bs1_c1",
                f"unexpected suggestion {nid}",
            )
        self.assertGreater(len(got), 0, "should suggest at least one triangle node")

    def test_never_returns_level1_textbook(self):
        got = suggest_nodes(["必修一"], NODES)
        self.assertNotIn("bx1", got)

    def test_empty_inputs_are_safe(self):
        self.assertEqual(suggest_nodes([], NODES), [])
        self.assertEqual(suggest_nodes(["等腰三角形"], []), [])
        self.assertEqual(suggest_nodes([""], NODES), [])
        self.assertEqual(suggest_nodes(None, NODES), [])

    def test_limit_is_respected(self):
        got = suggest_nodes(
            ["等腰三角形", "三角形中位线", "全等三角形", "集合的概念"],
            NODES,
            limit=2,
        )
        self.assertEqual(len(got), 2)

    def test_low_signal_labels_do_not_produce_noise(self):
        got = suggest_nodes(["无关的物理知识点abcdef"], NODES)
        self.assertEqual(got, [])

    def test_chapter_prefix_does_not_bleed_into_match(self):
        # "1.1" appearing in the label must not accidentally match all
        # "1.1 ..." nodes.
        got = suggest_nodes(["1.1"], NODES)
        self.assertEqual(got, [])

    def test_full_form_with_extra_wording_still_finds_node(self):
        got = suggest_nodes(["二次函数的图像与性质"], NODES)
        self.assertIn("bx2_c3_s2", got)


if __name__ == "__main__":
    unittest.main()
