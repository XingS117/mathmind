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

    def test_every_case_has_expected_image_count_and_existing_files(self):
        cases = load_acceptance_cases()

        self.assertEqual(
            {case["case_id"]: len(case["images"]) for case in cases},
            EXPECTED_IMAGE_COUNTS,
        )
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
