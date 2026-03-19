# 教师端 API：考试与阅卷

本页覆盖教师侧的组卷、发布、考试分析、阅卷任务、重考审批与成绩发布接口。

## 1. 智能组卷与考试管理

### POST /teacher/exams/ai-assemble

根据教师自然语言要求，从现有题库中挑题组卷。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 是 | 学科名称 |
| requirement | string | 是 | 自然语言要求，例如“单选题 5 道，填空题 3 道” |
| exclude_question_ids | array | 否 | 需要排除的题目 ID |

后端行为：

1. 从当前教师、当前学科题库中取题。
2. 解析自然语言中的题型与数量要求。
3. 对题干、解析、能力标签做关键词匹配。
4. 返回已匹配题目、已满足与未满足的要求块。

返回示例：

```json
{
  "questions": [],
  "matched_requirements": [
    {"label": "单选题", "count": 5, "matched_count": 5, "keywords": ["函数"]}
  ],
  "unmet_requirements": [],
  "summary": "已匹配 5 题，单选题 5/5 题"
}
```

### POST /teacher/exams/create

创建考试。若 `publish_now=true`，会直接以已发布状态创建，并在必要时自动修正开始结束时间窗口。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| title | string | 是 | 考试标题，同一教师下不可重复 |
| subject | string | 否 | 学科；可不传，后端会根据题目推断 |
| duration_minutes | integer | 是 | 时长 |
| start_time | datetime | 是 | 开始时间 |
| end_time | datetime | 是 | 结束时间 |
| publish_now | boolean | 否 | 是否立即发布 |
| instructions | string | 否 | 考试说明 |
| allow_review | boolean | 否 | 是否允许查看解析 |
| random_question_order | boolean | 否 | 是否随机题序 |
| class_ids | array | 是 | 绑定班级 ID 列表 |
| question_items | array | 是 | 题目数组 |

`question_items` 每项包含：`question_id`、`score`、`order_no`、`section_name`。

说明：

- 当 `subject` 为空时，后端会尝试从 `question_items` 关联题目中推断学科。

常见失败：

- `409`: 同一教师已有重名考试。
- `400`: 立即发布但未绑定班级。
- `400`: 立即发布但未添加题目。

### GET /teacher/exams

分页查询考试列表。

支持过滤参数：

- `status`
- `subject`
- `class_id`
- `keyword`
- `page`
- `page_size`

返回：

- `items`: Exam 对象数组。
- `total`: 总数。

`items` 中除基础字段外，当前实现还返回：

- `knowledge_points`: 当前试卷题目关联学科名称去重列表。
- `pending_review_count`: 该考试下待批阅主观题数量。

### GET /teacher/exams/detail

获取单场考试详情、题目清单与已绑定班级。

查询参数：`exam_id`。

返回结构：

- `exam`: 考试对象。
- `question_items`: 每题包含 `question_id`、`score`、`order_no`、`section_name`、`question`。
- `classes`: 班级对象数组。

### POST /teacher/exams/update

更新考试基础信息。

请求体中所有字段均可选，除 `exam_id` 外；若传了 `question_items`，后端会重算 `total_score`；若传了 `class_ids` 或 `question_items`，会重建关系数据。

### POST /teacher/exams/publish

将草稿考试发布为可作答状态。

请求体：

```json
{
  "exam_id": 1001
}
```

发布前校验：

1. 至少绑定 1 个班级。
2. 至少存在 1 道题。
3. 若原时间窗口已过期，会自动把开始时间调整到当前，结束时间顺延 `duration_minutes`。

成功返回：

```json
{
  "exam_id": 1001,
  "status": "published",
  "start_time": "2026-03-16T10:00:00",
  "end_time": "2026-03-16T11:30:00"
}
```

### POST /teacher/exams/pause

把考试状态改回 `draft`，用于暂停入口展示。

### POST /teacher/exams/finish

把考试状态改为 `finished` 并记录 `finished_at`。

### POST /teacher/exams/delete

删除考试。当前仅允许删除 `draft` 或 `finished` 状态考试，`published` 状态会被拒绝，防止误删进行中的教学任务。

删除时会同步清理：

- 学习任务
- 试卷题目关联
- 试卷班级关联

### POST /teacher/exams/ai-evaluate

对试卷进行结构分析并生成 AI 评价结果。

当前实现为规则占位，但已具备正式任务链路。

返回中的 `evaluation` 包含：

- `difficulty`
- `discrimination`
- `coverage_score`
- `structure_comments`
- `estimated_duration_minutes`

## 2. 考试洞察

### GET /teacher/exams/insights

从考试提交、错题和用时维度输出试卷分析结果。

查询参数：`exam_id`。

返回由三部分构成：

1. `progress`
   - `submitted_count`
   - `target_count`
   - `completion_rate`
2. `learning`
   - `avg_duration_minutes`
   - `avg_score`
   - `overall_wrong_rate`
3. `top_wrong_questions`
   - 每项包含 `question_id`、`stem`、`answer_count`、`wrong_count`、`wrong_rate`、`avg_spent_seconds`
4. `ai_summary`
   - `easy_mistakes`
   - `teaching_suggestions`

## 3. 阅卷与评分

### GET /teacher/review/objective-score

查看某份提交的客观题得分明细。

查询参数：`exam_id`、`submission_id`。

返回：

```json
{
  "submission_id": 9001,
  "objective_score": 58,
  "question_scores": [
    {"question_id": 101, "score": 5},
    {"question_id": 102, "score": 0}
  ]
}
```

### POST /teacher/review/ai-score

为某份提交发起 AI 主观题评分任务。

请求体：

| 字段 | 类型 | 必填 |
| --- | --- | --- |
| exam_id | integer | 是 |
| submission_id | integer | 是 |

当前返回 `task_id` 与 `status`，评分结果仍为占位实现。

### GET /teacher/review/items

获取某场考试下的主观题阅卷项，同时返回所有提交记录摘要，便于“有提交但无主观题”的场景也能展示学生。

查询参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| exam_id | integer | 考试 ID |
| review_status | string | 可选，按 `pending` 或 `reviewed` 过滤 |
| page | integer | 页码 |
| page_size | integer | 每页数量，最大 100 |

返回字段：

- `items`: ReviewItem 数组。
- `total`: 主观题阅卷项总数。
- `manual_review_required`: 是否存在需要人工阅卷的项目。
- `submissions`: 所有提交摘要数组。

`submissions` 每项包含：

- `submission_id`
- `student_id`
- `student_name`
- `status`
- `review_status`
- `submitted_at`
- `total_score`
- `manual_item_count`
- `pending_manual_count`

### GET /teacher/review/tasks

教师阅卷任务总览接口。

查询参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| view | string | `all`、`pending`、`completed` |
| page | integer | 页码 |
| page_size | integer | 每页数量 |

返回中的每个任务项包含：

- `exam_id`
- `exam_title`
- `subject`
- `exam_status`
- `total_submissions`
- `total_review_items`
- `pending_count`
- `reviewed_count`
- `ai_status`
- `task_status`
- `review_mode`: `manual` 或 `objective_only`
- `latest_submitted_at`

### POST /teacher/review/submit

提交单条主观题阅卷结果。

请求体：

| 字段 | 类型 | 必填 |
| --- | --- | --- |
| review_item_id | integer | 是 |
| final_score | number | 是 |
| review_comment | string | 否 |

后端会：

1. 更新 `ReviewItem.final_score` 和状态。
2. 记录一条 `ReviewLog` 方便追踪分数变更。

### POST /teacher/review/publish-results

发布某场考试成绩。

处理逻辑：

1. 汇总每份提交的主观题总分。
2. 计算 `total_score`。
3. 将提交状态更新为 `reviewed`，`review_status` 更新为 `completed`。
4. 按总分和提交时间生成班级排名。
5. 向每位学生推送 `results_published` WebSocket 事件。

返回：

```json
{
  "exam_id": 1001,
  "published": true
}
```

## 4. 重考审批

### GET /teacher/review/retake-requests

分页查看学生重考申请。

查询参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| status | string | 可选，按申请状态过滤 |
| page | integer | 页码 |
| page_size | integer | 每页数量 |

每个申请项包含：

- `request_id`
- `status`
- `exam_id`
- `exam_title`
- `student_id`
- `student_name`
- `reason`
- `created_at`
- `updated_at`
- `comment`

### POST /teacher/review/retake-requests/action

审批重考申请。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| request_id | integer | 是 | 申请任务 ID |
| action | string | 是 | `approve` 或 `reject` |
| comment | string | 否 | 审批备注 |

当 `action=approve` 时，后端会重置学生当前提交：

- 删除旧的 `ReviewItem` 与 `ReviewLog`
- 清空 `SubmissionAnswer`
- 把提交状态恢复为 `not_started`
- 清空分数、排名、AI 分析状态

返回：

```json
{
  "request_id": 7001,
  "status": "approved"
}
```
