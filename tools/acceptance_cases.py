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
    for case in cases:
        missing = REQUIRED_FIELDS - set(case)
        if missing:
            raise ValueError(
                f"{case.get('case_id', 'unknown')} missing fields: {sorted(missing)}"
            )
        if case["case_id"] in seen_ids:
            raise ValueError(f"Duplicate case_id: {case['case_id']}")
        seen_ids.add(case["case_id"])

        pages = [image["page"] for image in case["images"]]
        if pages != list(range(1, len(case["images"]) + 1)):
            raise ValueError(f"{case['case_id']} pages must be sequential from 1")

        normalized_case = dict(case)
        normalized_case["image_paths"] = [
            PROJECT_ROOT / image["path"] for image in case["images"]
        ]
        normalized_case["reference_path"] = PROJECT_ROOT / case["reference"]
        normalized.append(normalized_case)

    return normalized
