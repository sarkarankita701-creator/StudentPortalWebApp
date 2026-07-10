"""Validation for teacher-authored bulk-question JSON (Test Portal)."""
import json

REQUIRED_QUESTION_KEYS = ("question_text", "option_a", "option_b", "option_c", "option_d", "correct_option")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _is_nonempty_str(value):
    return isinstance(value, str) and value.strip() != ""


def validate_questions_json(raw_json):
    """Parse and validate a bulk-question JSON payload.

    Returns a normalized list of question dicts on success. Raises ValueError
    with a human-readable message (safe to flash to the user) on any problem.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno}).")

    _require(isinstance(data, dict) and isinstance(data.get("questions"), list),
              'JSON must be an object with a "questions" array, e.g. {"questions": [...]}.')
    questions = data["questions"]
    _require(len(questions) > 0, "At least one question is required.")

    normalized = []
    for i, q in enumerate(questions, start=1):
        _require(isinstance(q, dict), f"Question {i} must be an object.")
        for key in REQUIRED_QUESTION_KEYS:
            _require(_is_nonempty_str(q.get(key)), f'Question {i} needs non-empty "{key}".')
        correct_option = q["correct_option"].strip().lower()
        _require(correct_option in ("a", "b", "c", "d"),
                  f'Question {i} "correct_option" must be one of "a", "b", "c", "d".')
        marks = q.get("marks", 1)
        _require(isinstance(marks, int) and not isinstance(marks, bool) and marks > 0,
                  f'Question {i} "marks" must be a positive integer.')
        normalized.append({
            "question_text": q["question_text"].strip(),
            "option_a": q["option_a"].strip(),
            "option_b": q["option_b"].strip(),
            "option_c": q["option_c"].strip(),
            "option_d": q["option_d"].strip(),
            "correct_option": correct_option,
            "marks": marks,
        })
    return normalized
