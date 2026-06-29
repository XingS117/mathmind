import unittest

from tools.acceptance_scoring import (
    CRITICAL_DIMENSIONS,
    WEIGHTS,
    evaluate_case,
    weighted_score,
)


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
    def test_weighted_score_for_passing_scores_is_87_5(self):
        self.assertEqual(weighted_score(PASSING_SCORES), 87.5)

    def test_p0_issue_blocks_progress_even_with_perfect_score(self):
        scores = {dimension: 2 for dimension in PASSING_SCORES}

        result = evaluate_case(
            scores,
            issues=[{"severity": "P0"}],
            tutor_completed=True,
        )

        self.assertEqual(result["score"], 100.0)
        self.assertFalse(result["can_progress"])

    def test_zero_critical_dimension_blocks_progress(self):
        scores = {dimension: 2 for dimension in PASSING_SCORES}
        scores["diagram_semantics"] = 0

        result = evaluate_case(scores, issues=[], tutor_completed=True)

        self.assertFalse(result["can_progress"])
        self.assertIn("diagram_semantics", result["blocking_dimensions"])

    def test_all_dimensions_at_one_score_50_and_block_progress(self):
        scores = {dimension: 1 for dimension in PASSING_SCORES}

        result = evaluate_case(scores, issues=[], tutor_completed=True)

        self.assertEqual(result["score"], 50.0)
        self.assertFalse(result["can_progress"])

    def test_weighted_score_rejects_missing_or_extra_dimensions(self):
        missing_scores = dict(PASSING_SCORES)
        del missing_scores["multi_image"]
        extra_scores = {**PASSING_SCORES, "unexpected": 2}

        with self.assertRaisesRegex(ValueError, "missing"):
            weighted_score(missing_scores)
        with self.assertRaisesRegex(ValueError, "extra"):
            weighted_score(extra_scores)

    def test_weighted_score_rejects_invalid_values(self):
        for invalid_value in (-1, 3, 1.5, "2", None):
            with self.subTest(invalid_value=invalid_value):
                scores = dict(PASSING_SCORES)
                scores["multi_image"] = invalid_value
                with self.assertRaises(ValueError):
                    weighted_score(scores)

    def test_issues_must_be_a_list(self):
        scores = {dimension: 2 for dimension in PASSING_SCORES}

        for invalid in (None, "P0", ({"severity": "P0"},), 0, {"severity": "P0"}):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "issues"):
                    evaluate_case(scores, issues=invalid, tutor_completed=True)

    def test_every_issue_must_be_a_dict(self):
        scores = {dimension: 2 for dimension in PASSING_SCORES}

        with self.assertRaisesRegex(ValueError, "dict"):
            evaluate_case(
                scores,
                issues=["P0"],
                tutor_completed=True,
            )

        with self.assertRaisesRegex(ValueError, "dict"):
            evaluate_case(
                scores,
                issues=[{"severity": "P0"}, "not-a-dict"],
                tutor_completed=True,
            )

    def test_issue_severity_must_be_p0_p1_or_p2(self):
        scores = {dimension: 2 for dimension in PASSING_SCORES}

        for invalid_severity in ("P3", "PO", "", "p0", "critical", None):
            with self.subTest(invalid_severity=invalid_severity):
                with self.assertRaisesRegex(ValueError, "severity"):
                    evaluate_case(
                        scores,
                        issues=[{"severity": invalid_severity}],
                        tutor_completed=True,
                    )

    def test_issue_without_severity_key_is_rejected(self):
        scores = {dimension: 2 for dimension in PASSING_SCORES}

        with self.assertRaisesRegex(ValueError, "severity"):
            evaluate_case(
                scores,
                issues=[{"summary": "no severity"}],
                tutor_completed=True,
            )

    def test_can_progress_is_true_when_all_conditions_pass(self):
        scores = {dimension: 2 for dimension in PASSING_SCORES}

        result = evaluate_case(scores, issues=[], tutor_completed=True)

        self.assertTrue(result["can_progress"])
        self.assertEqual(result["score"], 100.0)
        self.assertFalse(result["has_p0"])
        self.assertEqual(result["blocking_dimensions"], [])
        self.assertTrue(result["tutor_completed"])

    def test_p1_issue_does_not_alone_block_progress(self):
        scores = {dimension: 2 for dimension in PASSING_SCORES}

        result = evaluate_case(
            scores,
            issues=[{"severity": "P1", "summary": "排版问题"}],
            tutor_completed=True,
        )

        self.assertTrue(result["can_progress"])
        self.assertEqual(result["score"], 100.0)
        self.assertEqual(result["blocking_dimensions"], [])

    def test_independent_weight_locks_for_seven_dimensions(self):
        expected_weight_map = {
            "multi_image": 15,
            "text_formula": 15,
            "diagram_semantics": 20,
            "structured_fields": 10,
            "solution_consistency": 20,
            "tutor_quality": 15,
            "diagnostic_quality": 5,
        }

        self.assertEqual(WEIGHTS, expected_weight_map)

        for dimension, weight in expected_weight_map.items():
            with self.subTest(dimension=dimension):
                scores = {key: 0 for key in expected_weight_map}
                scores[dimension] = 1
                self.assertEqual(weighted_score(scores), weight / 2)

    def test_tutor_completed_must_be_bool(self):
        scores = {dimension: 2 for dimension in PASSING_SCORES}

        for non_bool in (1, 0, "yes", None, [], 1.0):
            with self.subTest(non_bool=non_bool):
                with self.assertRaises((TypeError, ValueError)):
                    evaluate_case(scores, issues=[], tutor_completed=non_bool)

    def test_blocking_dimensions_returns_sorted_critical_only(self):
        scores = {dimension: 2 for dimension in PASSING_SCORES}
        scores["solution_consistency"] = 0
        scores["multi_image"] = 0
        scores["text_formula"] = 0

        result = evaluate_case(scores, issues=[], tutor_completed=True)

        expected = sorted(
            dimension
            for dimension in CRITICAL_DIMENSIONS
            if scores[dimension] == 0
        )
        self.assertEqual(result["blocking_dimensions"], expected)
        self.assertEqual(
            result["blocking_dimensions"],
            ["multi_image", "solution_consistency", "text_formula"],
        )

    def test_blocking_dimensions_preserves_order_with_single_zero(self):
        scores = {dimension: 2 for dimension in PASSING_SCORES}
        scores["text_formula"] = 0

        result = evaluate_case(scores, issues=[], tutor_completed=True)

        self.assertEqual(result["blocking_dimensions"], ["text_formula"])


if __name__ == "__main__":
    unittest.main()
