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


# 人教 B 版 (2019) 关键节: 用于覆盖节名与教学口径术语差距大的场景
BBAN_NODES = [
    {"id": "bx1_c1", "name": "第一章 集合与常用逻辑用语", "level": 2, "parent_id": "bx1"},
    {"id": "bx1_c1_s1", "name": "1.1 集合", "level": 3, "parent_id": "bx1_c1"},
    {"id": "bx1_c1_s2", "name": "1.2 常用逻辑用语", "level": 3, "parent_id": "bx1_c1"},
    {"id": "xb1_c2", "name": "第二章 平面解析几何", "level": 2, "parent_id": "xb1"},
    {"id": "xb1_c2_s2", "name": "2.2 直线及其方程", "level": 3, "parent_id": "xb1_c2"},
    {"id": "xb1_c2_s5", "name": "2.5 椭圆及其方程", "level": 3, "parent_id": "xb1_c2"},
    {"id": "xb1_c2_s6", "name": "2.6 双曲线及其方程", "level": 3, "parent_id": "xb1_c2"},
    {"id": "xb1_c2_s7", "name": "2.7 抛物线及其方程", "level": 3, "parent_id": "xb1_c2"},
    {"id": "bx4_c11", "name": "第十一章 立体几何初步", "level": 2, "parent_id": "bx4"},
    {"id": "bx4_c11_s1", "name": "11.1 空间几何体", "level": 3, "parent_id": "bx4_c11"},
    {"id": "bx4_c11_s6", "name": "11.6 简单几何体的再认识", "level": 3, "parent_id": "bx4_c11"},
    {"id": "xb2_c4", "name": "第四章 概率与统计", "level": 2, "parent_id": "xb2"},
    {"id": "xb2_c4_s1", "name": "4.1 条件概率与事件的独立性", "level": 3, "parent_id": "xb2_c4"},
    {"id": "xb2_c4_s2", "name": "4.2 随机变量", "level": 3, "parent_id": "xb2_c4"},
    {"id": "bx1", "name": "必修第一册", "level": 1, "parent_id": None},
    {"id": "xb1", "name": "选择性必修第一册", "level": 1, "parent_id": None},
    {"id": "bx4", "name": "必修第四册", "level": 1, "parent_id": None},
    {"id": "xb2", "name": "选择性必修第二册", "level": 1, "parent_id": None},
]


class SuggestNodesTest(unittest.TestCase):
    def test_matches_exact_and_suffix_variants(self):
        got = suggest_nodes(
            ["等腰三角形的性质", "三角形中位线定理", "全等三角形的判定与性质"],
            NODES,
        )
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
        got = suggest_nodes(["1.1"], NODES)
        self.assertEqual(got, [])

    def test_full_form_with_extra_wording_still_finds_node(self):
        got = suggest_nodes(["二次函数的图像与性质"], NODES)
        self.assertIn("bx2_c3_s2", got)

    # -- 人教 B 版 场景专项 --

    def test_bban_logic_terms_fall_back_to_chapter_leaf(self):
        # "充分条件" 等 B 版没有细节节, 应回落到 "1.2 常用逻辑用语"
        got = suggest_nodes(["充分条件与必要条件", "全称量词命题"], BBAN_NODES)
        self.assertIn("bx1_c1_s2", got)

    def test_bban_standard_equation_maps_to_specific_conic(self):
        # "椭圆的标准方程" 应命中 "2.5 椭圆及其方程", 不能顺带把
        # 双曲线/抛物线也带出来.
        got = suggest_nodes(["椭圆的标准方程", "焦点弦长"], BBAN_NODES)
        self.assertIn("xb1_c2_s5", got)
        self.assertNotIn("xb1_c2_s6", got)
        self.assertNotIn("xb1_c2_s7", got)

    def test_bban_hyperbola_asymptote_and_eccentricity(self):
        got = suggest_nodes(["双曲线的渐近线", "离心率"], BBAN_NODES)
        self.assertIn("xb1_c2_s6", got)

    def test_bban_solid_geometry_view_maps_to_space_shapes(self):
        # 三视图 / 三棱锥体积 在 B 版应回落到 "11.1 空间几何体"
        got = suggest_nodes(["三视图", "三棱锥体积"], BBAN_NODES)
        self.assertTrue(
            "bx4_c11_s1" in got or "bx4_c11_s6" in got,
            f"expected 11.1/11.6 in {got}",
        )

    def test_bban_random_variable_umbrella(self):
        # 正态分布 / 分布列 / 期望 都在 B 版的 "4.2 随机变量"
        got = suggest_nodes(["正态分布", "离散型随机变量的期望"], BBAN_NODES)
        self.assertIn("xb2_c4_s2", got)

    def test_bban_line_slope_matches_line_equation_section(self):
        got = suggest_nodes(["直线的斜率", "两点距离公式"], BBAN_NODES)
        self.assertIn("xb1_c2_s2", got)


if __name__ == "__main__":
    unittest.main()