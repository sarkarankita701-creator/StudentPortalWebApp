"""Validation for teacher-authored game session item JSON.

A game session is a mixed set of revision "items" a student plays through
for instant feedback (no formal grading, replayable). Four item types are
supported, matching what templates/games/play.html + static/js/game_play.js
know how to render:
- "flashcard": front/back card, self-assessed by the student.
- "mcq": a question with several options and one correct index.
- "true_false": a statement the student judges true or false.
- "fill_blank": a short-answer prompt matched case-insensitively.
"""
import json

ALLOWED_ITEM_TYPES = {"flashcard", "mcq", "true_false", "fill_blank"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _is_nonempty_str(value):
    return isinstance(value, str) and value.strip() != ""


def _validate_points(item, i):
    points = item.get("points", 1)
    _require(isinstance(points, int) and not isinstance(points, bool) and points > 0,
              f'Item {i} "points" must be a positive integer.')
    return points


def validate_game_items(raw_json):
    """Parse and validate a bulk game-item JSON payload.

    Returns a normalized list of item dicts on success. Raises ValueError
    with a human-readable message (safe to flash to the user) on any problem.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno}).")

    _require(isinstance(data, dict) and isinstance(data.get("items"), list),
              'JSON must be an object with an "items" array, e.g. {"items": [...]}.')
    items = data["items"]
    _require(len(items) > 0, "At least one item is required.")

    normalized = []
    for i, item in enumerate(items, start=1):
        _require(isinstance(item, dict) and "type" in item, f'Item {i} is missing a "type".')
        item_type = item["type"]
        _require(item_type in ALLOWED_ITEM_TYPES,
                  f'Item {i} has unknown type "{item_type}". '
                  f"Allowed types: {', '.join(sorted(ALLOWED_ITEM_TYPES))}.")
        points = _validate_points(item, i)

        if item_type == "flashcard":
            _require(_is_nonempty_str(item.get("front")), f'Item {i} (flashcard) needs non-empty "front".')
            _require(_is_nonempty_str(item.get("back")), f'Item {i} (flashcard) needs non-empty "back".')
            normalized.append({
                "type": "flashcard",
                "front": item["front"].strip(),
                "back": item["back"].strip(),
                "points": points,
            })
        elif item_type == "mcq":
            _require(_is_nonempty_str(item.get("question")), f'Item {i} (mcq) needs non-empty "question".')
            options = item.get("options")
            _require(isinstance(options, list) and len(options) >= 2,
                      f"Item {i} (mcq) needs an \"options\" array with at least 2 entries.")
            _require(all(_is_nonempty_str(o) for o in options),
                      f"Item {i} (mcq) options must all be non-empty strings.")
            correct_index = item.get("correct_index")
            _require(isinstance(correct_index, int) and not isinstance(correct_index, bool)
                      and 0 <= correct_index < len(options),
                      f'Item {i} (mcq) "correct_index" must be an integer index into "options".')
            explanation = item.get("explanation")
            _require(explanation is None or isinstance(explanation, str),
                      f'Item {i} (mcq) "explanation" must be a string if present.')
            normalized.append({
                "type": "mcq",
                "question": item["question"].strip(),
                "options": [o.strip() for o in options],
                "correct_index": correct_index,
                "explanation": (explanation or "").strip(),
                "points": points,
            })
        elif item_type == "true_false":
            _require(_is_nonempty_str(item.get("statement")), f'Item {i} (true_false) needs non-empty "statement".')
            answer = item.get("answer")
            _require(isinstance(answer, bool), f'Item {i} (true_false) "answer" must be true or false.')
            normalized.append({
                "type": "true_false",
                "statement": item["statement"].strip(),
                "answer": answer,
                "points": points,
            })
        elif item_type == "fill_blank":
            _require(_is_nonempty_str(item.get("text")), f'Item {i} (fill_blank) needs non-empty "text".')
            _require(_is_nonempty_str(item.get("answer")), f'Item {i} (fill_blank) needs non-empty "answer".')
            accepted = item.get("accepted_answers", [])
            _require(isinstance(accepted, list) and all(_is_nonempty_str(a) for a in accepted),
                      f'Item {i} (fill_blank) "accepted_answers" must be an array of non-empty strings if present.')
            normalized.append({
                "type": "fill_blank",
                "text": item["text"].strip(),
                "answer": item["answer"].strip(),
                "accepted_answers": [a.strip() for a in accepted],
                "points": points,
            })

    return normalized
