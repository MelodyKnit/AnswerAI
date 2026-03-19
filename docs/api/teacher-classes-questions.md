# 教师端 API：班级与题库

本页覆盖教师工作台中与班级管理、学生查看、题库管理直接相关的接口。

## 1. 教师看板总览

### GET /teacher/dashboard/overview

返回教师首页顶部指标、平均分趋势、风险学生列表和 AI 班级总结。

可选查询参数：`subject`。

返回重点字段：

- `exam_count`: 当前教师名下考试数量。
- `pending_review_count`: 待批阅主观题数量。
- `risk_student_count`: 风险学生数量。
- `avg_score_trend`: 最近考试平均分趋势。
- `ai_class_summary`: 概览文案。
- `risk_students`: 风险学生数组。

`risk_students` 每项包含：

- `student_id`、`student_name`
- `class_name`
- `exam_id`、`exam_title`
- `latest_score`
- `correct_rate`
- `risk_level`
- `weak_abilities`
- `weak_knowledge_points`
- `coaching_suggestions`

### GET /teacher/feedback/list

教师查看用户反馈列表，支持按分类、关键词和分页筛选。

查询参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| category | string | 可选：`bug`、`product`、`design`、`other` |
| keyword | string | 可选，按内容、页面路径、用户姓名、邮箱模糊匹配 |
| page | integer | 页码，默认 1 |
| page_size | integer | 每页数量，默认 20，最大 100 |

返回结构：

```json
{
  "items": [
    {
      "id": 1,
      "category": "bug",
      "content": "组卷页筛选后题目为空",
      "images": ["/uploads/feedback-1.png"],
      "page_path": "/app/teacher/exams/create",
      "client_role": "teacher",
      "client_name": "李老师",
      "client_email": "teacher@example.com",
      "created_at": "2026-03-16T10:00:00+00:00"
    }
  ],
  "total": 1,
  "summary": {
    "bug": 1,
    "product": 0,
    "design": 0,
    "other": 0
  },
  "page": 1,
  "page_size": 20
}
```

## 2. 班级管理

### GET /teacher/classes

分页返回当前教师创建的班级列表。

查询参数：`page`、`page_size`。

返回结构：

```json
{
  "items": [
    {
      "id": 11,
      "name": "高一1班",
      "grade_name": "高一",
      "subject": "数学",
      "teacher_id": 21,
      "student_count": 45,
      "invite_code": "CLS-ABC123",
      "status": "active",
      "created_at": "2026-03-16T10:00:00+00:00"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1,
  "total_pages": 1
}
```

### POST /teacher/classes/create

创建班级并自动生成邀请码。

请求体：

| 字段 | 类型 | 必填 |
| --- | --- | --- |
| name | string | 是 |
| grade_name | string | 是 |
| subject | string | 是 |

返回中的 `class.invite_code` 可直接用于学生加入班级。

### POST /teacher/classes/update

更新教师名下班级基础信息。

请求体：

| 字段 | 类型 | 必填 |
| --- | --- | --- |
| class_id | integer | 是 |
| name | string | 是 |
| grade_name | string | 是 |
| subject | string | 是 |

说明：

- `name`、`grade_name`、`subject` 会进行去空格后校验，任一为空返回 `400`。

成功返回：

```json
{
  "class": {
    "id": 11,
    "name": "高一1班",
    "grade_name": "高一",
    "subject": "数学",
    "invite_code": "CLS-ABC123"
  }
}
```

### GET /teacher/classes/detail

返回班级详情与最近考试数量。

查询参数：`class_id`。

返回字段：

- `class`
- `recent_exam_count`
- `student_count`

### GET /teacher/classes/students

分页获取班级学生列表。

查询参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| class_id | integer | 班级 ID |
| keyword | string | 学生姓名关键字 |
| risk_level | string | 当前实现仅原样回显，用于前端筛选占位 |
| page | integer | 页码 |
| page_size | integer | 每页数量 |

返回中每个学生项包含：`id`、`name`、`email`、`phone`、`grade_name`、`risk_level`。

### GET /teacher/classes/analysis

返回单个班级的学习分析数据，供班级学情看板使用。

查询参数：`class_id`。

返回重点字段：

- `overview`: 班级人数、考试数、均分、平均正确率、完成率。
- `risk_distribution`: 高风险/预警/稳定人数分布。
- `score_distribution`: 分段成绩分布。
- `exam_trend`: 最近考试趋势。
- `weak_knowledge_points`: 薄弱知识点统计（当前按 `subject` 聚合）。
- `question_type_performance`: 各题型表现。
- `focus_students`: 重点关注学生列表。
- `student_risks`: 学生风险列表。
- `ai_insight`: AI 总结与行动建议。

说明：

- 当班级无学生或无有效作答数据时，接口仍返回完整结构，并附带可执行的 `ai_insight.actions` 引导文案。

### POST /teacher/classes/students/invite

将现有学生加入班级，或将已失活关系恢复为激活状态。

请求体：

| 字段 | 类型 | 必填 |
| --- | --- | --- |
| class_id | integer | 是 |
| student_id | integer | 是 |

常见失败：

- `404`: 学生不存在或不是学生角色。
- `400`: 学生已在班级中。

### POST /teacher/classes/students/remove

将学生从班级中移除，底层实现是把 `ClassStudent.status` 改为 `inactive`。

请求体与邀请接口相同。

成功返回：

```json
{
  "class_id": 11,
  "student_id": 1,
  "student_count": 44
}
```

### GET /teacher/students/detail

按学生维度查看基本信息、所属班级和最近一次考试结果摘要。

查询参数：`student_id`。

返回字段：

- `student`
- `class`
- `latest_summary.latest_exam_id`
- `latest_summary.latest_total_score`

## 3. 题库管理

### GET /teacher/questions

分页查询当前教师题库。

支持过滤条件：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| subject | string | 学科名称 |
| type | string | 题型编码 |
| difficulty_min | number | 难度下限 |
| difficulty_max | number | 难度上限 |
| keyword | string | 题干关键字 |
| page | integer | 页码 |
| page_size | integer | 每页数量 |

返回：

- `items`: Question 对象数组。
- `total`: 总数。

### GET /teacher/questions/subjects

返回当前教师题库中实际存在题目的学科名称列表。

```json
{
  "items": ["数学", "物理"]
}
```

### GET /teacher/questions/detail

按 `question_id` 返回完整题目对象，用于独立题目详情页或题目编辑初始化。

### POST /teacher/questions/create

创建题目。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 是 | 学科名称 |
| type | string | 是 | 题型编码 |
| stem | string | 是 | 题干 |
| options | array | 否 | 选择题选项数组 |
| answer | array/string | 是 | 标准答案 |
| analysis | string | 否 | 解析 |
| score | number | 是 | 分值 |
| difficulty | number | 否 | 难度 |
| ability_tags | array | 否 | 能力标签 |

说明：

- `answer` 会被后端统一序列化保存。
- `ability_tags` 存入 `extra_meta`。
- 题目创建后会同步重建选项信息。

### POST /teacher/questions/update

更新题目，支持部分字段更新。

除 `question_id` 外，其余字段均可选；传了 `options` 时会重建选项。

### POST /teacher/questions/delete

删除题目，并同步清理试卷关联与相关学习任务。

请求体：

```json
{
  "question_id": 101
}
```

实现细节：

1. 若题目已被试卷引用，会先删除 `ExamQuestion` 关联。
2. 删除题目选项。
3. 若某场试卷因此变成“无有效题目”，会触发该试卷关联学习任务清理。

### POST /teacher/questions/import

当前为预留接口，已具备任务外壳，但尚未执行真实导题逻辑。

请求体：

| 字段 | 类型 | 必填 |
| --- | --- | --- |
| file_url | string | 否 |
| import_type | string | 是 |
| subject | string | 是 |

当前返回固定为：

```json
{
  "import_count": 0,
  "failed_count": 0,
  "errors": ["当前阶段未实现文件导题"],
  "task_id": "task_xxx"
}
```

### POST /teacher/questions/ai-generate

根据要求批量生成题目草稿。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 是 | 学科 |
| grade_name | string | 否 | 年级 |
| question_type | string | 是 | 题型 |
| requirement | string | 是 | 生成要求 |
| focus_topics | array | 否 | 聚焦主题关键词（如题型/能力点/章节主题） |
| difficulty | number | 否 | 难度 |
| count | integer | 否 | 题目数量，默认 1 |
| with_analysis | boolean | 否 | 是否生成解析 |

返回：

- `questions`: 生成结果数组。
- `used_model`: 实际使用的模型。
- `model_errors`: 模型调用失败信息数组。
- `task_id`: 对应 AI 任务 ID。

### POST /teacher/questions/ai-review

对单题执行 AI 质量审核占位逻辑。

请求体：

```json
{
  "question_id": 101
}
```

当前返回的 `review` 包含：

- `ambiguity_risk`
- `option_quality`
- `answer_consistency`
- `difficulty_estimation`
- `suggestions`

同时会把题目 `quality_status` 更新为 `reviewed`。
