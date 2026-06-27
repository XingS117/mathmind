import json
import tempfile
import unittest
from pathlib import Path

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
    def assert_invalid_manifest(self, manifest, expected_pattern):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "cases.json"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, expected_pattern):
                load_acceptance_cases(manifest_path)

    @staticmethod
    def valid_case():
        return {
            "case_id": "RQ-TEST",
            "title": "测试案例",
            "images": [{"page": 1, "path": "image.jpg"}],
            "reference": "reference.md",
            "capabilities": [],
            "risks": [],
        }

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
            self.assertTrue(case["reference_path"].is_absolute(), case["case_id"])
            self.assertTrue(case["reference_path"].is_file(), case["case_id"])
            for image in case["image_paths"]:
                self.assertTrue(image.is_absolute(), f"{case['case_id']}: {image}")
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

    def test_manifest_must_be_a_non_empty_list(self):
        for manifest in ({}, []):
            with self.subTest(manifest=manifest):
                self.assert_invalid_manifest(
                    manifest,
                    "Acceptance manifest must contain a non-empty list",
                )

    def test_case_must_be_an_object(self):
        self.assert_invalid_manifest(
            ["not-an-object"],
            "Case at index 0 must be an object",
        )

    def test_case_must_include_required_fields(self):
        case = self.valid_case()
        del case["title"]

        self.assert_invalid_manifest([case], "RQ-TEST missing fields:.*title")

    def test_case_ids_must_be_unique(self):
        case = self.valid_case()

        self.assert_invalid_manifest(
            [case, dict(case)],
            "Duplicate case_id: RQ-TEST",
        )

    def test_images_must_be_a_non_empty_list(self):
        for images in ("not-a-list", []):
            with self.subTest(images=images):
                case = self.valid_case()
                case["images"] = images
                self.assert_invalid_manifest(
                    [case],
                    "RQ-TEST images must be a non-empty list",
                )

    def test_image_must_be_an_object(self):
        case = self.valid_case()
        case["images"] = ["not-an-object"]

        self.assert_invalid_manifest(
            [case],
            "RQ-TEST image at index 0 must be an object",
        )

    def test_image_must_include_page_and_path(self):
        for missing_field in ("page", "path"):
            with self.subTest(missing_field=missing_field):
                case = self.valid_case()
                del case["images"][0][missing_field]
                self.assert_invalid_manifest(
                    [case],
                    f"RQ-TEST image at index 0 missing fields:.*{missing_field}",
                )

    def test_image_pages_must_be_sequential_from_one(self):
        case = self.valid_case()
        case["images"][0]["page"] = 2

        self.assert_invalid_manifest(
            [case],
            "RQ-TEST pages must be sequential from 1",
        )


if __name__ == "__main__":
    unittest.main()
