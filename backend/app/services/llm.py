import json
import random
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.schemas.teacher import AIQuestionGenerateRequest


def generate_questions_with_llm(payload: AIQuestionGenerateRequest) -> dict[str, Any]:
    """
    处理 generate questions with llm 请求并返回结果。
    """
    model_errors: list[dict[str, str]] = []

    for cfg in settings.llm_configs:
        try:
            generated = _call_single_model(cfg, payload)
            normalized = [_normalize_question(item, payload) for item in generated]
            return {
                "questions": normalized,
                "used_model": cfg.name,
                "model_errors": model_errors,
            }
        except Exception as exc:  # noqa: BLE001
            model_errors.append({"model": cfg.name, "error": str(exc)})

    return {
        "questions": [_fallback_question(payload)],
        "used_model": "fallback-rule-based",
        "model_errors": model_errors,
    }


def _call_single_model(cfg, payload: AIQuestionGenerateRequest) -> list[dict[str, Any]]:
    """
    处理  call single model 请求并返回结果。
    """
    client = OpenAI(base_url=cfg.url, api_key=cfg.key)
    prompt = _build_prompt(payload)
    completion = client.chat.completions.create(
        model=cfg.model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": "你是严谨的中小学出题助手，只输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
    )
    content = (completion.choices[0].message.content or "").strip()
    data = _extract_json(content)
    questions = data.get("questions", []) if isinstance(data, dict) else []
    if not isinstance(questions, list) or not questions:
        raise ValueError("模型返回结构不符合预期，缺少 questions 数组")
    return questions


def _build_prompt(payload: AIQuestionGenerateRequest) -> str:
    """
    处理  build prompt 请求并返回结果。
    """
    kp_text = "、".join(payload.knowledge_points) if payload.knowledge_points else "综合能力"
    difficulty = payload.difficulty if payload.difficulty is not None else 0.5
    return (
        "请按以下要求生成题目，并严格返回 JSON。\n"
        "返回格式：{\"questions\":[{\"subject\":str,\"type\":str,\"stem\":str,\"options\":[],\"answer\":str|list,\"analysis\":str}]}\n"
        f"学科：{payload.subject}\n"
        f"年级：{payload.grade_name or '不限'}\n"
        f"题型：{payload.question_type}\n"
        f"知识点：{kp_text}\n"
        f"难度：{difficulty}\n"
        f"数量：{max(1, payload.count)}\n"
        f"附加要求：{payload.requirement}\n"
        "注意：选择题请给 options（A/B/C/D）；判断题 answer 为 TRUE 或 FALSE；"
        "填空题 answer 用数组。"
    )


def _extract_json(raw: str) -> Any:
    """
    处理  extract json 请求并返回结果。
    """
    if not raw:
        raise ValueError("模型返回为空")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("模型返回非 JSON")
    return json.loads(raw[start : end + 1])


def _normalize_question(item: dict[str, Any], payload: AIQuestionGenerateRequest) -> dict[str, Any]:
    """
    处理  normalize question 请求并返回结果。
    """
    q_type = str(item.get("type") or payload.question_type)
    stem = str(item.get("stem") or "").strip()
    analysis = str(item.get("analysis") or "").strip()

    options = item.get("options") or []
    normalized_options: list[dict[str, str]] = []
    if q_type in {"single_choice", "multiple_choice"}:
        normalized_options = _normalize_options(options)

    answer = item.get("answer")
    normalized_answer = _normalize_answer(q_type, answer, normalized_options)

    return {
        "subject": payload.subject,
        "type": q_type,
        "stem": stem,
        "options": normalized_options,
        "answer": normalized_answer,
        "analysis": analysis,
        "score": 5,
        "difficulty": payload.difficulty if payload.difficulty is not None else 0.5,
        "knowledge_point_ids": [],
        "ability_tags": [],
    }


def _normalize_options(options: Any) -> list[dict[str, str]]:
    """
    处理  normalize options 请求并返回结果。
    """
    if not isinstance(options, list):
        options = []

    normalized: list[dict[str, str]] = []
    for index, item in enumerate(options):
        key = chr(65 + index)
        if isinstance(item, dict):
            key = str(item.get("key") or key).strip().upper()[:1] or key
            content = str(item.get("content") or "").strip()
        else:
            content = str(item).strip()
        if content:
            normalized.append({"key": key, "content": content})

    if len(normalized) < 2:
        normalized = [
            {"key": "A", "content": "选项A"},
            {"key": "B", "content": "选项B"},
            {"key": "C", "content": "选项C"},
            {"key": "D", "content": "选项D"},
        ]
    return normalized


def _normalize_answer(q_type: str, answer: Any, options: list[dict[str, str]]) -> Any:
    """
    处理  normalize answer 请求并返回结果。
    """
    if q_type == "multiple_choice":
        if isinstance(answer, list):
            picked = [str(x).strip().upper() for x in answer if str(x).strip()]
        else:
            picked = [x.strip().upper() for x in str(answer or "").split(",") if x.strip()]
        valid = {o["key"] for o in options}
        picked = [x for x in picked if x in valid]
        if not picked:
            picked = [options[0]["key"], options[1]["key"]]
        return picked

    if q_type == "single_choice":
        value = str(answer or "").strip().upper()
        valid = {o["key"] for o in options}
        return value if value in valid else options[0]["key"]

    if q_type == "judge":
        value = str(answer or "").strip().upper()
        if value in {"TRUE", "T", "对", "正确"}:
            return "TRUE"
        if value in {"FALSE", "F", "错", "错误"}:
            return "FALSE"
        return random.choice(["TRUE", "FALSE"])

    if q_type == "blank":
        if isinstance(answer, list):
            values = [str(x).strip() for x in answer if str(x).strip()]
            return values or ["示例答案"]
        value = str(answer or "").strip()
        return [value] if value else ["示例答案"]

    return str(answer or "").strip()


def _fallback_question(payload: AIQuestionGenerateRequest) -> dict[str, Any]:
    """
    处理  fallback question 请求并返回结果。
    """
    kp = payload.knowledge_points[0] if payload.knowledge_points else "综合能力"
    q_type = payload.question_type

    if q_type in {"single_choice", "multiple_choice"}:
        options = [
            {"key": "A", "content": "选项A"},
            {"key": "B", "content": "选项B"},
            {"key": "C", "content": "选项C"},
            {"key": "D", "content": "选项D"},
        ]
        answer = "A" if q_type == "single_choice" else ["A", "B"]
        return {
            "subject": payload.subject,
            "type": q_type,
            "stem": f"关于{kp}，下列说法正确的是：",
            "options": options,
            "answer": answer,
            "analysis": "占位结果：请根据教学目标进行微调。",
            "score": 5,
            "difficulty": payload.difficulty if payload.difficulty is not None else 0.5,
            "knowledge_point_ids": [],
            "ability_tags": [],
        }

    if q_type == "judge":
        return {
            "subject": payload.subject,
            "type": q_type,
            "stem": f"判断：{kp}相关结论总是成立。",
            "options": [],
            "answer": "FALSE",
            "analysis": "占位结果：该结论并非总成立。",
            "score": 5,
            "difficulty": payload.difficulty if payload.difficulty is not None else 0.5,
            "knowledge_point_ids": [],
            "ability_tags": [],
        }

    if q_type == "blank":
        return {
            "subject": payload.subject,
            "type": q_type,
            "stem": f"请填写与{kp}相关的关键术语：____。",
            "options": [],
            "answer": ["示例答案"],
            "analysis": "占位结果：可替换为课程重点词汇。",
            "score": 5,
            "difficulty": payload.difficulty if payload.difficulty is not None else 0.5,
            "knowledge_point_ids": [],
            "ability_tags": [],
        }

    return {
        "subject": payload.subject,
        "type": q_type,
        "stem": f"请围绕{kp}进行作答。",
        "options": [],
        "answer": "示例答案",
        "analysis": "占位结果：请根据教学内容完善。",
        "score": 5,
        "difficulty": payload.difficulty if payload.difficulty is not None else 0.5,
        "knowledge_point_ids": [],
        "ability_tags": [],
    }
