WEIGHTS = {
    "multi_image": 15,
    "text_formula": 15,
    "diagram_semantics": 20,
    "structured_fields": 10,
    "solution_consistency": 20,
    "tutor_quality": 15,
    "diagnostic_quality": 5,
}

CRITICAL_DIMENSIONS = {
    "multi_image",
    "text_formula",
    "diagram_semantics",
    "solution_consistency",
}

ALLOWED_SEVERITIES = {"P0", "P1", "P2"}


def _validate_issues(issues) -> None:
    if not isinstance(issues, list):
        raise ValueError(
            f"issues must be a list, got {type(issues).__name__}"
        )
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            raise ValueError(
                f"issue at index {index} must be a dict, "
                f"got {type(issue).__name__}"
            )
        severity = issue.get("severity")
        if severity not in ALLOWED_SEVERITIES:
            raise ValueError(
                f"issue at index {index} severity must be one of "
                f"{sorted(ALLOWED_SEVERITIES)}, got {severity!r}"
            )


def weighted_score(scores: dict[str, int]) -> float:
    missing = set(WEIGHTS) - set(scores)
    extra = set(scores) - set(WEIGHTS)
    if missing or extra:
        raise ValueError(
            f"Score dimensions mismatch: missing={sorted(missing)}, "
            f"extra={sorted(extra)}"
        )

    for dimension, score in scores.items():
        if (
            not isinstance(score, int)
            or isinstance(score, bool)
            or score not in {0, 1, 2}
        ):
            raise ValueError(f"Invalid score for {dimension}: {score!r}")

    total = sum(
        (scores[dimension] / 2) * weight
        for dimension, weight in WEIGHTS.items()
    )
    return round(total, 1)


def evaluate_case(
    scores: dict[str, int],
    issues: list[dict],
    tutor_completed: bool,
) -> dict:
    if not isinstance(tutor_completed, bool):
        raise TypeError(
            f"tutor_completed must be bool, got {type(tutor_completed).__name__}"
        )
    _validate_issues(issues)

    score = weighted_score(scores)
    blocking_dimensions = sorted(
        dimension
        for dimension in CRITICAL_DIMENSIONS
        if scores[dimension] == 0
    )
    has_p0 = any(issue["severity"] == "P0" for issue in issues)
    can_progress = (
        score >= 80
        and not has_p0
        and not blocking_dimensions
        and tutor_completed is True
    )

    return {
        "score": score,
        "has_p0": has_p0,
        "blocking_dimensions": blocking_dimensions,
        "tutor_completed": tutor_completed,
        "can_progress": can_progress,
    }
