import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "acceptance" / "real-question-cases.json"
REQUIRED_FIELDS = {"case_id", "title", "images", "reference", "capabilities", "risks"}


def load_acceptance_cases(manifest_path: Path = DEFAULT_MANIFEST) -> list[dict]:
    with manifest_path.open(encoding="utf-8") as handle:
        cases = json.load(handle)

    if not isinstance(cases, list) or not cases:
        raise ValueError("Acceptance manifest must contain a non-empty list")

    seen_ids: set[str] = set()
    normalized: list[dict] = []
    for case_index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case at index {case_index} must be an object")

        case_context = case.get("case_id", f"Case at index {case_index}")
        missing = REQUIRED_FIELDS - set(case)
        if missing:
            raise ValueError(
                f"{case_context} missing fields: {sorted(missing)}"
            )
        if not isinstance(case["case_id"], str) or not case["case_id"]:
            raise ValueError(
                f"Case at index {case_index} case_id must be a non-empty string"
            )
        if case["case_id"] in seen_ids:
            raise ValueError(f"Duplicate case_id: {case['case_id']}")
        seen_ids.add(case["case_id"])

        images = case["images"]
        if not isinstance(images, list) or not images:
            raise ValueError(f"{case['case_id']} images must be a non-empty list")

        pages = []
        for image_index, image in enumerate(images):
            image_context = f"{case['case_id']} image at index {image_index}"
            if not isinstance(image, dict):
                raise ValueError(f"{image_context} must be an object")
            missing_image_fields = {"page", "path"} - set(image)
            if missing_image_fields:
                raise ValueError(
                    f"{image_context} missing fields: {sorted(missing_image_fields)}"
                )
            if not isinstance(image["page"], int) or isinstance(image["page"], bool):
                raise ValueError(f"{image_context} page must be an integer")
            if not isinstance(image["path"], str):
                raise ValueError(f"{image_context} path must be a string")
            pages.append(image["page"])

        if pages != list(range(1, len(images) + 1)):
            raise ValueError(f"{case['case_id']} pages must be sequential from 1")
        if not isinstance(case["reference"], str):
            raise ValueError(f"{case['case_id']} reference must be a string")

        normalized_case = dict(case)
        normalized_case["image_paths"] = [
            PROJECT_ROOT / image["path"] for image in images
        ]
        normalized_case["reference_path"] = PROJECT_ROOT / case["reference"]
        normalized.append(normalized_case)

    return normalized
