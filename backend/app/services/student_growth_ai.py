import json
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.services.ai_client import request_chat_completion


@dataclass(frozen=True)
class Book:
    title: str
    author: str
    isbn: str
    link: str
    reason: str


@dataclass(frozen=True)
class AbilityRule:
    topic: str
    keywords: tuple[str, ...]
    abilities: tuple[str, ...]
    books: tuple[Book, ...]


ENGINEERING_BOOKS = (
    Book(
        title="Engineering Drawing and Design",
        author="David A. Madsen, David P. Madsen",
        isbn="9781337564873",
        link="https://www.worldcat.org/isbn/9781337564873",
        reason="覆盖工程制图基础、3D 表达和工程图规范，适合系统补强构图能力。",
    ),
    Book(
        title="Technical Drawing with Engineering Graphics",
        author="Frederick E. Giesecke et al.",
        isbn="9780135090485",
        link="https://www.worldcat.org/isbn/9780135090485",
        reason="强化投影、三视图与工程图表达，适合提升空间理解与图形转换能力。",
    ),
)

MATH_BOOKS = (
    Book(
        title="How to Solve It",
        author="George Polya",
        isbn="9780691164071",
        link="https://www.worldcat.org/isbn/9780691164071",
        reason="经典解题方法论，帮助建立数学建模与分步推理能力。",
    ),
)

PHYSICS_BOOKS = (
    Book(
        title="Fundamentals of Physics",
        author="David Halliday, Robert Resnick, Jearl Walker",
        isbn="9781118230713",
        link="https://www.worldcat.org/isbn/9781118230713",
        reason="系统覆盖物理建模与定量分析，适合夯实概念到题目应用的链路。",
    ),
)

ENGLISH_BOOKS = (
    Book(
        title="English Grammar in Use",
        author="Raymond Murphy",
        isbn="9781108457656",
        link="https://www.worldcat.org/isbn/9781108457656",
        reason="适合巩固语法与阅读理解基础，提升语言准确表达能力。",
    ),
)

ABILITY_RULES: tuple[AbilityRule, ...] = (
    AbilityRule(
        topic="工程绘图",
        keywords=(
            "工程绘图",
            "工程制图",
            "机械制图",
            "cad",
            "autocad",
            "solidworks",
            "三视图",
            "投影",
            "轴测图",
            "三维",
            "3d",
            "构图",
            "装配图",
            "零件图",
        ),
        abilities=("3D构图能力", "工程构图思维能力", "图形空间理解能力"),
        books=ENGINEERING_BOOKS,
    ),
    AbilityRule(
        topic="数学建模",
        keywords=("函数", "方程", "几何", "概率", "统计", "导数", "极值", "数列", "证明"),
        abilities=("数学建模能力", "逻辑推理能力", "运算准确能力"),
        books=MATH_BOOKS,
    ),
    AbilityRule(
        topic="物理分析",
        keywords=("受力", "电路", "能量", "速度", "加速度", "动量", "波", "光学", "电磁"),
        abilities=("物理建模能力", "公式迁移能力", "实验理解能力"),
        books=PHYSICS_BOOKS,
    ),
    AbilityRule(
        topic="英语理解",
        keywords=("完形", "阅读", "语法", "写作", "词汇", "时态", "从句", "翻译"),
        abilities=("阅读理解能力", "语言表达能力", "语法应用能力"),
        books=ENGLISH_BOOKS,
    ),
)

DEFAULT_ABILITIES = ("审题能力", "知识迁移能力", "稳定作答能力")

QUESTION_TYPE_LABELS: dict[str, str] = {
    "single_choice": "单选题",
    "multiple_choice": "多选题",
    "true_false": "判断题",
    "fill_blank": "填空题",
    "short_answer": "简答题",
    "programming": "编程题",
    "essay": "论述题",
    "case": "案例题",
}

SUBJECT_HINT_TOPIC: tuple[tuple[tuple[str, ...], str], ...] = (
    (("数学", "math"), "数学建模"),
    (("物理", "physics"), "物理分析"),
    (("英语", "english"), "英语理解"),
    (("工程", "制图", "cad", "机械"), "工程绘图"),
)


def build_growth_ability_profile(
    answer_records: list[dict[str, Any]],
    refine_with_llm: bool = True,
) -> dict[str, Any]:
    if not answer_records:
        return {
            "ability_profile": [],
            "ai_summary": "暂无足够作答记录，完成至少一次考试后可生成能力画像。",
            "ai_actions": ["先完成一次完整测验，系统会基于真实作答题目生成能力诊断。"],
            "recommended_books": [],
            "topic_distribution": [],
            "question_type_distribution": [],
            "prompt_version": "growth-profile-v2",
        }

    topic_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0.0, "correct": 0.0})
    ability_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0.0, "correct": 0.0})
    question_type_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0.0, "correct": 0.0})
    matched_books: dict[str, dict[str, Any]] = {}

    for row in answer_records:
        stem = str(row.get("stem") or "")
        analysis = str(row.get("analysis") or "")
        subject = str(row.get("subject") or "")
        q_type = str(row.get("question_type") or "")
        is_correct = bool(row.get("is_correct") is True)
        type_label = QUESTION_TYPE_LABELS.get(q_type, q_type or "未分类题型")

        question_type_stats[type_label]["count"] += 1
        question_type_stats[type_label]["correct"] += 1 if is_correct else 0

        corpus = f"{subject} {q_type} {stem} {analysis}".lower()
        matched_rule = _select_best_rule(corpus, subject)

        if not matched_rule:
            topic = subject.strip() or "综合能力"
            topic_stats[topic]["count"] += 1
            topic_stats[topic]["correct"] += 1 if is_correct else 0
            for ability in DEFAULT_ABILITIES:
                ability_stats[ability]["count"] += 1
                ability_stats[ability]["correct"] += 1 if is_correct else 0
            continue

        topic_stats[matched_rule.topic]["count"] += 1
        topic_stats[matched_rule.topic]["correct"] += 1 if is_correct else 0
        for ability in matched_rule.abilities:
            ability_stats[ability]["count"] += 1
            ability_stats[ability]["correct"] += 1 if is_correct else 0
        for book in matched_rule.books:
            if book.isbn not in matched_books:
                matched_books[book.isbn] = {
                    "title": book.title,
                    "author": book.author,
                    "isbn": book.isbn,
                    "link": book.link,
                    "reason": book.reason,
                    "related_topics": [matched_rule.topic],
                }
            elif matched_rule.topic not in matched_books[book.isbn]["related_topics"]:
                matched_books[book.isbn]["related_topics"].append(matched_rule.topic)

    total_answers = max(1, len(answer_records))
    ability_profile: list[dict[str, Any]] = []
    for name, stats in ability_stats.items():
        count = int(stats["count"])
        if count == 0:
            continue
        accuracy = stats["correct"] / count
        coverage = count / total_answers
        score = int(round(max(35, min(95, (accuracy * 0.5 + coverage * 0.5) * 100))))
        ability_profile.append(
            {
                "name": name,
                "value": score,
                "question_count": count,
                "accuracy": round(accuracy, 2),
                "reason": f"基于 {count} 道相关题目，正确率 {round(accuracy * 100)}%。",
            }
        )

    ability_profile.sort(key=lambda item: item["value"], reverse=True)

    topic_distribution = []
    for topic, stats in topic_stats.items():
        count = int(stats["count"])
        accuracy = (stats["correct"] / count) if count else 0.0
        topic_distribution.append(
            {
                "topic": topic,
                "question_count": count,
                "accuracy": round(accuracy, 2),
            }
        )
    topic_distribution.sort(key=lambda item: item["question_count"], reverse=True)

    question_type_distribution = []
    for type_name, stats in question_type_stats.items():
        count = int(stats["count"])
        accuracy = (stats["correct"] / count) if count else 0.0
        question_type_distribution.append(
            {
                "type": type_name,
                "question_count": count,
                "accuracy": round(accuracy, 2),
            }
        )
    question_type_distribution.sort(key=lambda item: item["question_count"], reverse=True)

    ai_actions = _build_actions(ability_profile, topic_distribution, question_type_distribution)
    ai_summary = _build_summary(ability_profile, topic_distribution)

    recommended_books = list(matched_books.values())
    recommended_books.sort(key=lambda item: len(item["related_topics"]), reverse=True)
    recommended_books = recommended_books[:6]

    if refine_with_llm:
        llm_refined = _try_refine_with_llm(
            {
                "ability_profile": ability_profile,
                "topic_distribution": topic_distribution,
                "ai_summary": ai_summary,
                "ai_actions": ai_actions,
                "recommended_books": recommended_books,
            }
        )
        if llm_refined:
            ai_summary = llm_refined.get("ai_summary") or ai_summary
            ai_actions = llm_refined.get("ai_actions") or ai_actions

    ai_actions = _sanitize_ai_actions(ai_actions, topic_distribution)

    return {
        "ability_profile": ability_profile[:8],
        "ai_summary": ai_summary,
        "ai_actions": ai_actions[:8],
        "recommended_books": recommended_books,
        "topic_distribution": topic_distribution[:8],
        "question_type_distribution": question_type_distribution[:8],
        "prompt_version": "growth-profile-v2",
    }


def _select_best_rule(corpus: str, subject: str) -> AbilityRule | None:
    matched = []
    for rule in ABILITY_RULES:
        score = sum(1 for keyword in rule.keywords if keyword.lower() in corpus)
        if score > 0:
            matched.append((score, rule))

    if not matched:
        return None

    subject_lower = subject.strip().lower()
    hinted_topic = ""
    for hints, topic in SUBJECT_HINT_TOPIC:
        if any(hint in subject_lower for hint in hints):
            hinted_topic = topic
            break

    if hinted_topic:
        hinted = [item for item in matched if item[1].topic == hinted_topic]
        if hinted:
            hinted.sort(key=lambda item: item[0], reverse=True)
            return hinted[0][1]
        return None

    matched.sort(key=lambda item: item[0], reverse=True)
    return matched[0][1]


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        if keyword.lower() in text:
            return True
    return False


def _build_actions(
    ability_profile: list[dict[str, Any]],
    topic_distribution: list[dict[str, Any]],
    question_type_distribution: list[dict[str, Any]],
) -> list[str]:
    actions: list[str] = []
    weakest_ability = sorted(ability_profile, key=lambda item: item["value"])[:1]
    if weakest_ability:
        item = weakest_ability[0]
        actions.append(
            f"能力补强｜{item['name']} 当前得分 {item['value']} 分。"
            f"建议连续 5 天做“2 道基础 + 1 道变式”小练，并在每题后写 1 句错因复盘。"
        )

    weak_topics = [item for item in topic_distribution if item["accuracy"] < 0.65][:1]
    if weak_topics:
        topic = weak_topics[0]
        actions.append(
            f"主题突破｜{topic['topic']} 当前正确率约 {round(topic['accuracy'] * 100)}%。"
            f"本周至少完成 {max(6, topic['question_count'])} 题同主题训练，按“先例题-再独立作答-再对照答案”三步执行。"
        )

    weak_types = sorted(question_type_distribution, key=lambda item: item["accuracy"])[:1]
    if weak_types:
        weak_type = weak_types[0]
        actions.append(
            f"题型专项｜{weak_type['type']} 正确率约 {round(weak_type['accuracy'] * 100)}%。"
            "建议做题时固定“三段式”：先圈关键词，再列步骤，再写结论，减少会而不对的情况。"
        )

    if ability_profile:
        top = ability_profile[0]
        actions.append(
            f"迁移巩固｜你在 {top['name']} 维度相对更稳。"
            "每次复习最后加 1 道综合题，把优势能力迁移到薄弱主题，提升整体稳定性。"
        )

    if not actions:
        actions.append("当前能力较均衡，建议继续保持每周至少两次错题复盘。")
    return _dedupe_actions(actions)


def _sanitize_ai_actions(actions: list[str], topic_distribution: list[dict[str, Any]]) -> list[str]:
    available_topics = {str(item.get("topic") or "").strip() for item in topic_distribution}
    available_topics.discard("")
    known_topics = [rule.topic for rule in ABILITY_RULES]

    filtered: list[str] = []
    for action in actions:
        text = str(action or "").strip()
        if not text:
            continue
        # 避免生成与当前作答主题无关的学科动作（如未作答数学却出现数学建议）
        conflict = False
        for topic in known_topics:
            if topic in text and topic not in available_topics:
                conflict = True
                break
        if not conflict:
            filtered.append(text)

    return _dedupe_actions(filtered)


def _dedupe_ordered(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def _dedupe_actions(actions: list[str]) -> list[str]:
    # 优先按完整文案去重，再按“意图签名”去重，避免表述不同但建议同质化。
    exact = _dedupe_ordered(actions)
    seen_signatures: set[str] = set()
    output: list[str] = []
    for action in exact:
        signature = _action_signature(action)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        output.append(action)
    return output


def _action_signature(text: str) -> str:
    head = str(text or "").split("｜", 1)[0]
    normalized = re.sub(r"\d+", "", head)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized.strip()


def _build_summary(ability_profile: list[dict[str, Any]], topic_distribution: list[dict[str, Any]]) -> str:
    if not ability_profile:
        return "暂无能力画像数据。"

    strongest = ability_profile[0]
    weakest = sorted(ability_profile, key=lambda item: item["value"])[0]
    topic = topic_distribution[0]["topic"] if topic_distribution else "当前学科"
    return (
        f"你最近的作答题目主要集中在{topic}，"
        f"当前优势能力是{strongest['name']}（{strongest['value']}分），"
        f"相对短板是{weakest['name']}（{weakest['value']}分），"
        "建议按照 AI 行动建议做 1-2 周专项训练后复测。"
    )


def _try_refine_with_llm(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not settings.llm_configs:
        return None

    prompt = (
        "你是学习分析助手。请基于给定 JSON，输出更可执行的中文总结和行动建议。"
        "必须只输出 JSON，格式为{\"ai_summary\":str,\"ai_actions\":[str,...]}。"
        "禁止编造书籍，不要改动书籍列表。行动建议要短句、可落地。\n"
        f"输入JSON：{json.dumps(payload, ensure_ascii=False)}"
    )

    for cfg in settings.llm_configs:
        try:
            content = request_chat_completion(
                cfg=cfg,
                scene="student_growth_profile_refine",
                system_prompt="你是严谨的学习成长分析助手，只输出 JSON。",
                user_prompt=prompt,
                temperature=0.3,
            )
            data = _extract_json(content)
            if isinstance(data, dict):
                actions = data.get("ai_actions")
                if isinstance(actions, list):
                    data["ai_actions"] = [str(item) for item in actions if str(item).strip()]
                return data
        except Exception:
            continue
    return None


def _extract_json(raw: str) -> Any:
    if not raw:
        raise ValueError("empty model output")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(raw[start : end + 1])
