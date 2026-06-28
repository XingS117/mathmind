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


if __name__ == "__main__":
    unittest.main()
