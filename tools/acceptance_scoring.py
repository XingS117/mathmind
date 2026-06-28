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
    score = weighted_score(scores)
    blocking_dimensions = sorted(
        dimension
        for dimension in CRITICAL_DIMENSIONS
        if scores[dimension] == 0
    )
    has_p0 = any(issue.get("severity") == "P0" for issue in issues)
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
