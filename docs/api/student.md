# 学生端 API

本页覆盖学生角色当前可用的考试、成绩、成长画像、班级和学习任务接口。所有接口都要求学生身份，除非特别注明。

## 1. 考试列表与详情

### GET /student/exams

返回当前学生所属班级下、且试卷中确实存在题目的考试列表。

查询参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| status | string | 可选：`upcoming`、`ongoing`、`finished` |
| subject | string | 学科名称 |
| page | integer | 页码 |
| page_size | integer | 每页数量，最大 100 |

返回中的每个考试项包含：

- `id`、`title`、`subject`
- `duration_minutes`
- `status`
- `start_time`、`end_time`
- `submission_status`
- `has_submitted`
- `retake_request_status`
- `retake_request_created_at`

### GET /student/exams/detail

根据 `exam_id` 返回单场考试详情与学生是否可进入考试。

查询参数：

| 参数 | 类型 | 必填 |
| --- | --- | --- |
| exam_id | integer | 是 |

返回结构：

```json
{
  "exam": {
    "id": 1001,
    "title": "高一数学周测",
    "subject": "数学",
    "duration_minutes": 90,
    "total_score": 100,
    "status": "published",
    "start_time": "2026-03-16T08:00:00Z",
    "end_time": "2026-03-16T09:30:00Z",
    "instructions": "请独立完成作答",
    "question_count": 20
  },
  "can_start": true,
  "rules": {
    "allow_review": true,
    "random_question_order": false
  }
}
```

## 2. 开始考试与取卷

### POST /student/exams/start

用于初始化或恢复学生提交记录。若是已审批通过的重考，会重置旧提交内容并重新进入作答。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

主要行为：

1. 校验学生是否在该考试绑定班级中。
2. 首次进入时创建 `ExamSubmission`。
3. 若存在已批准的重考申请，则清空旧答案、行为日志与成绩。
4. 推送实时事件 `submission_started`。

成功返回：

```json
{
  "submission": {
    "id": 9001,
    "exam_id": 1001,
    "student_id": 1,
    "status": "in_progress",
    "started_at": "2026-03-16T08:02:00+00:00",
    "submitted_at": null,
    "deadline_at": "2026-03-16T09:30:00+00:00",
    "objective_score": 0,
    "subjective_score": 0,
    "total_score": 0,
    "correct_rate": 0,
    "ranking_in_class": null
  },
  "paper_token": "paper_9001"
}
```

常见失败：

- `400`: 考试未开放或不在可作答时间窗。
- `400`: 学生未绑定到该考试的任何班级。
- `404`: 考试不存在或试卷无有效题目。

### GET /student/exams/paper

返回实际答题页所需题目内容。

查询参数：

| 参数 | 类型 | 必填 |
| --- | --- | --- |
| exam_id | integer | 是 |
| submission_id | integer | 是 |

返回重点：

- `exam`: 试卷基础信息。
- `questions`: 题目数组，每项包含 `question_id`、`type`、`stem`、`score`、`options`。
- `remaining_seconds`: 按提交记录截止时间实时计算的剩余秒数。

说明：

- 选择题选项使用 `key` 和 `content`，前端提交答案时要以选项键值为准。

## 3. 作答过程接口

### POST /student/exams/answer/save

保存单题作答草稿。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 提交记录 ID |
| question_id | integer | 是 | 题目 ID |
| answer | array/string/null | 否 | 客观题答案 |
| answer_text | string/null | 否 | 主观题文本 |
| spent_seconds | integer | 否 | 本题耗时 |
| mark_difficult | boolean | 否 | 是否标记为难题 |
| favorite | boolean | 否 | 是否收藏 |

返回：

```json
{
  "saved": true,
  "answer_version": 3,
  "saved_at": "2026-03-16T08:20:00+00:00"
}
```

同时会通过考试 WebSocket 推送 `answer_saved` 事件。

### POST /student/exams/answers/save-batch

批量保存多题答案，适合页面切换或定时自动保存。

请求体中的 `answers` 为数组，每项包含：`question_id`、`answer`、`answer_text`、`spent_seconds`。

返回：

```json
{
  "saved_count": 5
}
```

### POST /student/exams/behavior/report

上报考试行为事件，例如切屏、停留、跳题等。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 提交记录 ID |
| events | array | 是 | 行为事件数组 |

事件项字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| question_id | integer/null | 可为空，表示非题目级事件 |
| event_type | string | 事件名称 |
| occurred_at | datetime | 发生时间 |
| payload | object/null | 附加数据 |

返回：

```json
{
  "received": true,
  "event_count": 3
}
```

### GET /student/exams/pre-submit-check

正式交卷前执行漏答检查与提醒生成。

查询参数：`exam_id`、`submission_id`。

返回内容：

- `unanswered_question_ids`: 未作答题目 ID 列表。
- `marked_question_ids`: 被学生标记为难题的题目 ID 列表。
- `subjective_warnings`: 针对未作答主观题的提醒文本。
- `ai_reminders`: 提交前的提示语。

### POST /student/exams/submit

学生正式交卷。接口会同时完成客观题判分、主观题待阅卷项生成、考试分析任务触发和学习计划任务触发。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 提交记录 ID |
| confirm_submit | boolean | 是 | 必须为 `true` |

主要行为：

1. 校验学生是否确认交卷。
2. 对客观题即时判分并累计 `objective_score`。
3. 对主观题自动创建 `ReviewItem`，进入教师阅卷流程。
4. 将提交状态设为 `submitted`。
5. 同步触发 `exam_analysis` 和 `study_plan_generate` 两个 AI 任务。
6. 推送 `submission_submitted` 实时事件。

返回示例：

```json
{
  "submission": {
    "id": 9001,
    "exam_id": 1001,
    "student_id": 1,
    "status": "submitted",
    "objective_score": 58,
    "subjective_score": 0,
    "total_score": 58,
    "correct_rate": 0.58,
    "ranking_in_class": null
  },
  "triggered_tasks": [
    {"task_id": "task_exam_analysis_xxx", "type": "exam_analysis", "status": "completed"},
    {"task_id": "task_study_plan_xxx", "type": "study_plan_generate", "status": "completed"}
  ]
}
```

## 4. 重考申请

### POST /student/exams/retake-request

对已提交或已评阅的考试发起重考申请。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| reason | string | 否 | 申请原因，后端会截断到 500 字 |

返回：

```json
{
  "request_id": 7001,
  "status": "pending",
  "created_at": "2026-03-16T10:00:00+00:00"
}
```

若最近一条申请仍处于 `pending` 或 `approved`，接口不会重复创建，而是直接返回已有申请。

## 5. 学生首页与成绩分析

### GET /student/dashboard/overview

返回学生工作台概览信息。

可选查询参数：`subject`。

返回重点字段：

- `upcoming_exam_count`
- `recent_exams`
- `latest_result_summary`
- `ai_reminders`
- `ability_profile_summary`
- `recommended_tasks`

说明：

- 接口会先清理失效学习计划与重复任务，再生成首页推荐数据。

### GET /student/results/overview

返回某场考试的成绩概览。

查询参数：`exam_id`。

返回字段包括：

- `submission`
- `score_summary`
- `ranking_summary`
- `type_score_distribution`
- `ai_summary`
- `risk_alerts`

### GET /student/results/question-analysis

返回单题级复盘详情，适合错题详情页。

查询参数：

| 参数 | 类型 | 必填 |
| --- | --- | --- |
| exam_id | integer | 是 |
| question_id | integer | 是 |

返回结构由三部分组成：

- `question`: 题目内容、解析、选项。
- `answer`: 学生答案、标准答案、得分、正误。
- `diagnosis`: 当前诊断类型、原因、修复步骤与下一步动作。

### POST /student/ai-chat/follow-up

学生围绕某道题继续追问 AI，获取简短辅导回答。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| question_id | integer | 是 | 题目 ID |
| messages | array | 是 | 对话消息，至少要有一条有效内容 |

消息项字段：`role`、`content`。

返回：

```json
{
  "reply": "先比较你的答案与标准答案差异，再重做一题同类型题验证。",
  "context": {
    "exam_id": 1001,
    "question_id": 101
  }
}
```

## 6. 成长画像与班级信息

### GET /student/knowledge-map

按历史作答正确率生成学生知识图谱。当前实现的节点粒度以题型为主，而非章节知识点树。

可选查询参数：`subject`。

返回：

- `nodes`: 每个节点包含 `id`、`name`、`mastery`、`status`。
- `edges`: 当前实现固定为空数组。
- `summary`: 图谱总结文案。

### GET /student/growth-trend

返回最多最近 10 次已提交考试的成长趋势数据。

可选查询参数：`subject`。

返回：

```json
{
  "exams": [
    {"date": "2026-03-01", "score": 78, "class_avg": 71.5},
    {"date": "2026-03-10", "score": 84, "class_avg": 74.2}
  ],
  "insights": ["最近一次考试成绩提升了6分，继续保持！"]
}
```

### GET /student/growth/ability-profile

基于真实作答记录生成能力画像、AI 建议、图表数据和推荐资源。

查询参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| subject | string | 可选，按学科过滤作答记录 |
| force_refresh | boolean | 可选，是否强制跳过缓存重新生成 |

实现特点：

- 后端会根据作答记录数量和最近更新时间生成缓存指纹。
- 默认 20 分钟缓存。
- 若 `force_refresh=true`，则忽略已有缓存重新计算。

返回体除画像本身外，还会附带：

```json
{
  "cache": {
    "hit": false,
    "fingerprint": "12:2026-03-16T09:30:00",
    "cached_at": "2026-03-16T10:00:00+00:00",
    "ttl_seconds": 1200
  }
}
```

### GET /student/classes

返回当前学生已加入的班级列表。

每个班级项包含：

- `class_id`
- `name`
- `grade_name`
- `subject`
- `teacher_name`
- `joined_at`

## 7. 学习任务

### GET /student/study-tasks

返回学生当前学习任务、已忽略任务和 AI 总览建议。

返回结构：

- `tasks`: 活跃任务列表。
- `ignored_tasks`: 已忽略任务列表。
- `ai_overview`: 包含 `readiness_score`、`active_task_count`、`completed_count`、`focus_types`、`summary` 等。
- `ai_actions`: 建议动作列表。

### POST /student/study-tasks/action

对单个学习任务执行状态流转。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| task_id | integer | 是 | 任务 ID |
| action | string | 是 | `start`、`pause`、`complete`、`ignore`、`unignore`、`delete` |
| feedback | string | 否 | 反馈文本，最多保留 1000 字 |

返回：

```json
{
  "task": {
    "id": 801,
    "status": "completed",
    "completed_at": "2026-03-16T10:20:00+00:00",
    "feedback": "本轮已完成复盘"
  }
}
```

若动作为 `delete`，返回中的状态固定为 `deleted`。

### GET /student/study-tasks/coaching

获取任务复习包，返回步骤建议与对应训练题。

查询参数：`task_id`。

返回字段：

- `task`: 任务基础信息。
- `coach_summary`: 本次复习摘要。
- `drill_steps`: 推荐执行步骤。
- `practice_items`: 最多 6 道历史错题或近似题，每项包含 `question_id`、`exam_id`、`question_type`、`stem`、`analysis`、`standard_answer`、`last_student_answer`、`practice_status`。
