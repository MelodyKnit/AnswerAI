import json


OBJECTIVE_TYPES = {"single_choice", "multiple_choice", "judge", "blank"}
SUBJECTIVE_TYPES = {"essay", "material", "short_answer"}


def parse_answer(raw: str | None):
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def serialize_answer(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def compute_objective_score(question_type: str, standard_answer, student_answer, full_score: float) -> tuple[bool | None, float]:
    if question_type not in OBJECTIVE_TYPES:
        return None, 0.0

    if question_type in {"single_choice", "judge"}:
        is_correct = standard_answer == student_answer
        return is_correct, float(full_score if is_correct else 0)

    if question_type == "multiple_choice":
        standard = sorted(standard_answer or [])
        student = sorted(student_answer or [])
        is_correct = standard == student
        return is_correct, float(full_score if is_correct else 0)

    if question_type == "blank":
        standard = str(standard_answer).strip() if standard_answer is not None else ""
        student = str(student_answer).strip() if student_answer is not None else ""
        is_correct = standard == student
        return is_correct, float(full_score if is_correct else 0)

    return None, 0.0
