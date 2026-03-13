# AI考试答题平台数据库设计文档

本文档基于 README 中定义的产品模块与 docs/api.md 中定义的接口设计，给出数据库层的实体划分、核心表结构、字段建议、索引建议、状态枚举与表关系说明，用于指导后端使用 FastAPI + SQLAlchemy 实现数据模型。

## 1. 设计目标

数据库设计需要同时支撑以下业务目标：

1. 支撑教师出题、组卷、发布考试、阅卷、分析的完整流程。
2. 支撑学生在线作答、自动保存、行为记录、交卷与错题复盘。
3. 支撑 AI 阅卷、AI 学情诊断、AI 对话、AI 学习计划、AI 报告的异步任务体系。
4. 支撑长期成长追踪，让学生和教师能持续查看历史趋势。
5. 支撑后续从 SQLite 平滑迁移到 MySQL 或 PostgreSQL。

## 2. 数据库选型建议

### 2.1 开发环境

- 推荐使用 SQLite。
- 优点是启动成本低、便于本地开发。

### 2.2 生产环境

- 推荐使用 PostgreSQL，次选 MySQL 8.x。
- 原因是更适合处理：
  - 较复杂的统计分析查询
  - JSON 字段存储
  - 并发写入
  - 任务与日志数据增长

## 3. 命名规范

### 3.1 表命名

- 使用小写蛇形命名。
- 使用复数表名。
- 示例：`users`、`exam_submissions`、`submission_answers`

### 3.2 字段命名

- 主键统一为 `id`。
- 外键统一为 `{entity}_id`，例如 `student_id`、`exam_id`。
- 时间字段统一使用：
  - `created_at`
  - `updated_at`
  - `deleted_at`，如果启用软删除

### 3.3 状态字段

- 状态字段统一使用字符串枚举，避免过度使用数字码导致可读性差。

## 4. 实体分层

数据库实体建议分为 7 层：

1. 用户与组织层：用户、班级、班级成员关系。
2. 题库层：题目、知识点、题目知识点映射。
3. 考试层：考试、试卷题目、班级考试分配。
4. 作答层：考试提交、答案、行为事件、收藏与标记。
5. 阅卷层：主观题复核、得分明细、评分历史。
6. AI 能力层：AI 任务、AI 对话、学习计划、报告。
7. 分析沉淀层：学生画像快照、班级分析快照、知识点掌握快照。

## 5. 核心表清单

建议第一阶段至少包含以下核心表：

1. `users`
2. `classes`
3. `class_students`
4. `subjects`
5. `knowledge_points`
6. `questions`
7. `question_options`
8. `question_knowledge_points`
9. `exams`
10. `exam_questions`
11. `exam_classes`
12. `exam_submissions`
13. `submission_answers`
14. `submission_behavior_events`
15. `review_items`
16. `review_logs`
17. `ai_tasks`
18. `ai_chat_sessions`
19. `ai_chat_messages`
20. `study_plans`
21. `study_tasks`
22. `reports`
23. `student_profile_snapshots`
24. `class_analysis_snapshots`
25. `knowledge_mastery_snapshots`

## 6. 详细表结构设计

以下字段类型以通用关系型数据库为基础描述：

- `bigint`：主键与主要外键
- `varchar(n)`：短文本
- `text`：长文本
- `numeric(10,2)`：分数等精确值
- `float`：统计性分值、难度系数
- `boolean`：布尔值
- `json`：结构化扩展数据
- `timestamp`：时间字段

---

## 6.1 users

用途：存储平台用户，包含教师和学生。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 用户 ID |
| role | varchar(20) | idx | 角色，student、teacher、admin |
| name | varchar(100) |  | 姓名 |
| email | varchar(150) | unique | 邮箱 |
| phone | varchar(30) | idx | 手机号 |
| password_hash | varchar(255) |  | 密码哈希 |
| avatar_url | varchar(255) |  | 头像 |
| school_name | varchar(150) | idx | 学校名称 |
| grade_name | varchar(50) | idx | 年级名称 |
| status | varchar(20) | idx | active、disabled |
| last_login_at | timestamp |  | 最后登录时间 |
| created_at | timestamp | idx | 创建时间 |
| updated_at | timestamp |  | 更新时间 |

说明：

- 教师和学生统一放在同一张表，通过 `role` 区分。
- 密码只存储哈希值，不存储明文。

推荐索引：

- unique(`email`)
- index(`role`, `status`)
- index(`school_name`, `grade_name`)

---

## 6.2 classes

用途：存储教师管理的班级。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 班级 ID |
| teacher_id | bigint | idx | 所属教师 ID |
| name | varchar(100) |  | 班级名称 |
| grade_name | varchar(50) | idx | 年级 |
| subject | varchar(50) | idx | 学科 |
| invite_code | varchar(50) | unique | 班级邀请码 |
| student_count | integer |  | 冗余学生数量 |
| status | varchar(20) | idx | active、archived |
| created_at | timestamp | idx | 创建时间 |
| updated_at | timestamp |  | 更新时间 |

外键：

- `teacher_id -> users.id`

推荐索引：

- unique(`invite_code`)
- index(`teacher_id`, `status`)

---

## 6.3 class_students

用途：学生和班级的关系表。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 关系 ID |
| class_id | bigint | idx | 班级 ID |
| student_id | bigint | idx | 学生 ID |
| teacher_id | bigint | idx | 归属教师 ID |
| joined_at | timestamp |  | 加入时间 |
| status | varchar(20) | idx | active、removed |
| created_at | timestamp |  | 创建时间 |

约束建议：

- unique(`class_id`, `student_id`)

外键：

- `class_id -> classes.id`
- `student_id -> users.id`
- `teacher_id -> users.id`

---

## 6.4 subjects

用途：学科字典表。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 学科 ID |
| code | varchar(50) | unique | 学科编码 |
| name | varchar(50) | unique | 学科名称 |
| sort_order | integer |  | 排序 |
| status | varchar(20) | idx | active、disabled |

---

## 6.5 knowledge_points

用途：知识点树结构。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 知识点 ID |
| subject_id | bigint | idx | 学科 ID |
| parent_id | bigint | idx | 父级知识点 ID |
| name | varchar(150) | idx | 知识点名称 |
| path | varchar(500) | idx | 树路径，例如 数学/函数/函数性质 |
| level | integer | idx | 层级 |
| sort_order | integer |  | 排序 |
| status | varchar(20) | idx | active、disabled |
| created_at | timestamp |  | 创建时间 |

外键：

- `subject_id -> subjects.id`
- `parent_id -> knowledge_points.id`

推荐索引：

- index(`subject_id`, `parent_id`)
- index(`subject_id`, `level`)

---

## 6.6 questions

用途：题库主表。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 题目 ID |
| created_by | bigint | idx | 创建教师 ID |
| subject_id | bigint | idx | 学科 ID |
| type | varchar(30) | idx | 题型 |
| stem | text |  | 题干 |
| answer_text | text |  | 标准答案文本或 JSON 字符串 |
| analysis | text |  | 解析 |
| score | numeric(10,2) |  | 默认分值 |
| difficulty | float | idx | 难度系数 |
| source | varchar(50) | idx | manual、import、ai_generate |
| quality_status | varchar(20) | idx | draft、reviewed、published |
| ai_review_summary | text |  | AI 审核摘要 |
| extra_meta | json |  | 扩展结构，例如公式、图片、富文本 |
| created_at | timestamp | idx | 创建时间 |
| updated_at | timestamp |  | 更新时间 |

说明：

- 单选、多选、判断、填空、简答题统一建模。
- 选择题选项独立放在 `question_options`。

外键：

- `created_by -> users.id`
- `subject_id -> subjects.id`

推荐索引：

- index(`created_by`, `subject_id`)
- index(`type`, `difficulty`)
- index(`source`, `quality_status`)

---

## 6.7 question_options

用途：存储选择题选项。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 选项 ID |
| question_id | bigint | idx | 题目 ID |
| option_key | varchar(10) |  | 选项编码，如 A、B |
| content | text |  | 选项内容 |
| sort_order | integer |  | 顺序 |
| created_at | timestamp |  | 创建时间 |

约束建议：

- unique(`question_id`, `option_key`)

---

## 6.8 question_knowledge_points

用途：题目和知识点多对多映射。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 关系 ID |
| question_id | bigint | idx | 题目 ID |
| knowledge_point_id | bigint | idx | 知识点 ID |
| weight | float |  | 权重，默认 1 |
| created_at | timestamp |  | 创建时间 |

约束建议：

- unique(`question_id`, `knowledge_point_id`)

---

## 6.9 exams

用途：考试主表。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 考试 ID |
| created_by | bigint | idx | 创建教师 ID |
| subject_id | bigint | idx | 学科 ID |
| title | varchar(200) | idx | 考试标题 |
| duration_minutes | integer |  | 时长 |
| total_score | numeric(10,2) |  | 总分 |
| status | varchar(20) | idx | draft、published、ongoing、finished、archived |
| instructions | text |  | 考试说明 |
| allow_review | boolean |  | 是否允许回看 |
| random_question_order | boolean |  | 是否随机题序 |
| start_time | timestamp | idx | 开始时间 |
| end_time | timestamp | idx | 结束时间 |
| published_at | timestamp |  | 发布时间 |
| finished_at | timestamp |  | 结束时间 |
| ai_evaluation_result | json |  | AI 试卷评估结果 |
| created_at | timestamp | idx | 创建时间 |
| updated_at | timestamp |  | 更新时间 |

外键：

- `created_by -> users.id`
- `subject_id -> subjects.id`

推荐索引：

- index(`created_by`, `status`)
- index(`start_time`, `end_time`)
- index(`subject_id`, `status`)

---

## 6.10 exam_questions

用途：考试与题目关系表，表示一张试卷由哪些题组成。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 关系 ID |
| exam_id | bigint | idx | 考试 ID |
| question_id | bigint | idx | 题目 ID |
| score | numeric(10,2) |  | 当前试卷下该题分值 |
| order_no | integer | idx | 题目顺序 |
| section_name | varchar(100) |  | 所属分区，例如 选择题、简答题 |
| created_at | timestamp |  | 创建时间 |

约束建议：

- unique(`exam_id`, `question_id`)
- unique(`exam_id`, `order_no`)

---

## 6.11 exam_classes

用途：考试分配到哪些班级。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 关系 ID |
| exam_id | bigint | idx | 考试 ID |
| class_id | bigint | idx | 班级 ID |
| created_at | timestamp |  | 创建时间 |

约束建议：

- unique(`exam_id`, `class_id`)

---

## 6.12 exam_submissions

用途：学生某次考试的一次作答提交。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 提交 ID |
| exam_id | bigint | idx | 考试 ID |
| student_id | bigint | idx | 学生 ID |
| class_id | bigint | idx | 班级 ID |
| teacher_id | bigint | idx | 教师 ID |
| status | varchar(20) | idx | not_started、in_progress、submitted、reviewed |
| started_at | timestamp | idx | 开始时间 |
| submitted_at | timestamp | idx | 提交时间 |
| deadline_at | timestamp |  | 截止时间 |
| objective_score | numeric(10,2) |  | 客观题得分 |
| subjective_score | numeric(10,2) |  | 主观题得分 |
| total_score | numeric(10,2) | idx | 总分 |
| correct_rate | float |  | 正确率 |
| ranking_in_class | integer |  | 班级排名 |
| review_status | varchar(20) | idx | pending、reviewing、completed |
| ai_analysis_status | varchar(20) | idx | pending、running、completed、failed |
| created_at | timestamp | idx | 创建时间 |
| updated_at | timestamp |  | 更新时间 |

约束建议：

- unique(`exam_id`, `student_id`)

推荐索引：

- index(`exam_id`, `class_id`)
- index(`exam_id`, `total_score`)
- index(`student_id`, `created_at`)

---

## 6.13 submission_answers

用途：存储学生逐题答案。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 答案 ID |
| submission_id | bigint | idx | 提交 ID |
| exam_id | bigint | idx | 考试 ID |
| question_id | bigint | idx | 题目 ID |
| answer_content | text |  | 答案内容，可存 JSON 字符串 |
| answer_text | text |  | 主观题文本 |
| is_correct | boolean | idx | 是否正确 |
| score | numeric(10,2) |  | 当前题得分 |
| spent_seconds | integer |  | 用时 |
| answer_version | integer |  | 答案版本号 |
| mark_difficult | boolean | idx | 是否标记疑难 |
| favorite | boolean | idx | 是否收藏 |
| ai_error_analysis | json |  | AI 错因分析结果 |
| created_at | timestamp |  | 创建时间 |
| updated_at | timestamp | idx | 更新时间 |

约束建议：

- unique(`submission_id`, `question_id`)

推荐索引：

- index(`submission_id`, `is_correct`)
- index(`question_id`, `is_correct`)

---

## 6.14 submission_behavior_events

用途：记录考试过程中的行为事件。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 事件 ID |
| submission_id | bigint | idx | 提交 ID |
| exam_id | bigint | idx | 考试 ID |
| question_id | bigint | idx | 题目 ID，可为空 |
| event_type | varchar(50) | idx | focus、blur、switch、change_answer 等 |
| payload | json |  | 扩展事件数据 |
| occurred_at | timestamp | idx | 事件发生时间 |
| created_at | timestamp |  | 写入时间 |

推荐索引：

- index(`submission_id`, `occurred_at`)
- index(`question_id`, `event_type`)

---

## 6.15 review_items

用途：主观题待复核记录。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 复核项 ID |
| exam_id | bigint | idx | 考试 ID |
| submission_id | bigint | idx | 提交 ID |
| question_id | bigint | idx | 题目 ID |
| student_id | bigint | idx | 学生 ID |
| ai_suggest_score | numeric(10,2) |  | AI 建议分数 |
| final_score | numeric(10,2) |  | 最终分数 |
| ai_comment | text |  | AI 评分说明 |
| teacher_comment | text |  | 教师评语 |
| review_status | varchar(20) | idx | pending、reviewed |
| reviewed_by | bigint | idx | 复核教师 ID |
| reviewed_at | timestamp |  | 复核时间 |
| created_at | timestamp | idx | 创建时间 |

推荐索引：

- index(`exam_id`, `review_status`)
- index(`submission_id`, `question_id`)

---

## 6.16 review_logs

用途：记录每次评分修改历史，用于审计。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 日志 ID |
| review_item_id | bigint | idx | 复核项 ID |
| operator_id | bigint | idx | 操作人 ID |
| old_score | numeric(10,2) |  | 旧分数 |
| new_score | numeric(10,2) |  | 新分数 |
| comment | text |  | 操作说明 |
| created_at | timestamp | idx | 操作时间 |

---

## 6.17 ai_tasks

用途：统一管理 AI 异步任务。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 自增 ID |
| task_id | varchar(100) | unique | 外部任务 ID |
| type | varchar(50) | idx | exam_analysis、ai_score、report_generate、study_plan_generate |
| status | varchar(20) | idx | pending、running、success、failed |
| progress | integer |  | 进度 0-100 |
| resource_type | varchar(50) | idx | submission、report、session、exam |
| resource_id | bigint | idx | 关联资源 ID |
| request_payload | json |  | 请求参数快照 |
| result_payload | json |  | 结果快照 |
| error_message | text |  | 错误信息 |
| created_by | bigint | idx | 发起人 ID |
| created_at | timestamp | idx | 创建时间 |
| updated_at | timestamp | idx | 更新时间 |
| finished_at | timestamp |  | 完成时间 |

推荐索引：

- unique(`task_id`)
- index(`type`, `status`)
- index(`resource_type`, `resource_id`)

---

## 6.18 ai_chat_sessions

用途：AI 辅导对话会话。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 自增 ID |
| session_id | varchar(100) | unique | 对外会话 ID |
| student_id | bigint | idx | 学生 ID |
| exam_id | bigint | idx | 考试 ID |
| question_id | bigint | idx | 关联题目 ID，可为空 |
| mode | varchar(50) | idx | wrong_question_tutor、knowledge_tutor、practice_tutor |
| context_snapshot | json |  | 创建会话时的上下文快照 |
| status | varchar(20) | idx | active、closed |
| created_at | timestamp | idx | 创建时间 |
| updated_at | timestamp |  | 更新时间 |

---

## 6.19 ai_chat_messages

用途：会话消息记录。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 消息 ID |
| session_id | bigint | idx | 会话主键 ID |
| sender_role | varchar(20) | idx | student、assistant、system |
| message_type | varchar(30) | idx | text、suggestion、quiz、similar_question |
| content | text |  | 消息文本 |
| extra_payload | json |  | 扩展结构 |
| created_at | timestamp | idx | 创建时间 |

推荐索引：

- index(`session_id`, `created_at`)

---

## 6.20 study_plans

用途：学生学习计划主表。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 学习计划 ID |
| student_id | bigint | idx | 学生 ID |
| subject_id | bigint | idx | 学科 ID |
| source_exam_id | bigint | idx | 来源考试 ID，可为空 |
| plan_type | varchar(30) | idx | daily、weekly、sprint |
| title | varchar(200) |  | 计划标题 |
| summary | text |  | AI 计划摘要 |
| status | varchar(20) | idx | active、completed、archived |
| ai_generation_task_id | bigint | idx | 关联 AI 任务 ID |
| start_date | timestamp |  | 开始时间 |
| end_date | timestamp |  | 结束时间 |
| created_at | timestamp | idx | 创建时间 |
| updated_at | timestamp |  | 更新时间 |

---

## 6.21 study_tasks

用途：学习计划下的任务项。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 任务 ID |
| plan_id | bigint | idx | 计划 ID |
| student_id | bigint | idx | 学生 ID |
| title | varchar(200) |  | 任务标题 |
| task_type | varchar(50) | idx | review、practice、quiz、video |
| knowledge_point_id | bigint | idx | 知识点 ID，可为空 |
| priority | integer | idx | 优先级 |
| estimated_minutes | integer |  | 预计耗时 |
| status | varchar(20) | idx | pending、completed |
| feedback | text |  | 学生反馈 |
| completed_at | timestamp |  | 完成时间 |
| created_at | timestamp | idx | 创建时间 |

---

## 6.22 reports

用途：AI 报告中心。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 报告 ID |
| report_type | varchar(30) | idx | exam、class、student、knowledge_topic |
| title | varchar(200) | idx | 标题 |
| exam_id | bigint | idx | 考试 ID，可为空 |
| class_id | bigint | idx | 班级 ID，可为空 |
| student_id | bigint | idx | 学生 ID，可为空 |
| status | varchar(20) | idx | generating、ready、failed |
| summary | text |  | 报告摘要 |
| content_json | json |  | 报告结构化内容 |
| file_url | varchar(255) |  | 导出文件地址 |
| version_no | integer |  | 版本号 |
| generated_by_task_id | bigint | idx | 关联 AI 任务 ID |
| created_by | bigint | idx | 创建人 |
| created_at | timestamp | idx | 创建时间 |
| updated_at | timestamp |  | 更新时间 |

推荐索引：

- index(`report_type`, `status`)
- index(`exam_id`, `class_id`, `student_id`)

---

## 6.23 student_profile_snapshots

用途：保存学生画像快照，避免每次都实时重算。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 快照 ID |
| student_id | bigint | idx | 学生 ID |
| subject_id | bigint | idx | 学科 ID |
| source_exam_id | bigint | idx | 来源考试 ID，可为空 |
| profile_json | json |  | 画像详情 |
| ai_summary | text |  | AI 总结 |
| created_at | timestamp | idx | 快照时间 |

---

## 6.24 class_analysis_snapshots

用途：班级考试分析快照。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 快照 ID |
| class_id | bigint | idx | 班级 ID |
| exam_id | bigint | idx | 考试 ID |
| analysis_json | json |  | 分析详情 |
| ai_conclusion | text |  | AI 结论 |
| created_at | timestamp | idx | 快照时间 |

约束建议：

- unique(`class_id`, `exam_id`)

---

## 6.25 knowledge_mastery_snapshots

用途：学生或班级层面的知识掌握快照。

| 字段 | 类型 | 主键/索引 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | 快照 ID |
| owner_type | varchar(20) | idx | student、class |
| owner_id | bigint | idx | 学生 ID 或班级 ID |
| subject_id | bigint | idx | 学科 ID |
| knowledge_point_id | bigint | idx | 知识点 ID |
| mastery_score | float | idx | 掌握程度 |
| wrong_count | integer |  | 失误次数 |
| source_exam_id | bigint | idx | 来源考试 ID，可为空 |
| created_at | timestamp | idx | 快照时间 |

推荐索引：

- index(`owner_type`, `owner_id`, `subject_id`)
- index(`knowledge_point_id`, `created_at`)

## 7. 关键表关系说明

核心关系可以概括为：

1. 一个教师可以有多个班级。
2. 一个班级有多个学生，学生通过 `class_students` 与班级关联。
3. 一个教师可以创建多个题目和考试。
4. 一场考试可以分配给多个班级。
5. 一场考试包含多个题目，一道题也可以被多场考试复用。
6. 一个学生在一场考试中只有一条提交记录。
7. 一次提交包含多条逐题答案记录。
8. 一次提交可产生多条行为事件、多个 AI 任务和多个复核项。
9. 一个学生可以有多个 AI 会话、多个学习计划和多个画像快照。
10. 一场考试可生成多个报告和多个分析快照。

## 8. 简化 ER 关系图

```text
users(teacher) 1 --- n classes
users(student) n --- n classes 通过 class_students

users(teacher) 1 --- n questions
questions n --- n knowledge_points 通过 question_knowledge_points

users(teacher) 1 --- n exams
exams n --- n questions 通过 exam_questions
exams n --- n classes 通过 exam_classes

exams 1 --- n exam_submissions
users(student) 1 --- n exam_submissions
exam_submissions 1 --- n submission_answers
exam_submissions 1 --- n submission_behavior_events
exam_submissions 1 --- n review_items

exam_submissions 1 --- n ai_tasks
users(student) 1 --- n ai_chat_sessions
ai_chat_sessions 1 --- n ai_chat_messages

users(student) 1 --- n study_plans
study_plans 1 --- n study_tasks

exams/classes/students 1 --- n reports
students/classes 1 --- n snapshots
```

## 9. 与 API 文档的映射关系

### 9.1 认证与账户接口

- `/auth/register`
- `/auth/login`
- `/auth/me`

主要使用表：

- `users`
- `classes`
- `class_students`

### 9.2 教师班级与学生管理接口

- `/teacher/classes`
- `/teacher/classes/detail`
- `/teacher/classes/students`

主要使用表：

- `classes`
- `class_students`
- `users`

### 9.3 教师题库与出题接口

- `/teacher/questions`
- `/teacher/questions/create`
- `/teacher/questions/ai-generate`

主要使用表：

- `questions`
- `question_options`
- `question_knowledge_points`
- `knowledge_points`
- `ai_tasks`

### 9.4 考试管理接口

- `/teacher/exams`
- `/teacher/exams/create`
- `/teacher/exams/ai-evaluate`

主要使用表：

- `exams`
- `exam_questions`
- `exam_classes`
- `ai_tasks`

### 9.5 学生考试接口

- `/student/exams`
- `/student/exams/start`
- `/student/exams/paper`
- `/student/exams/submit`

主要使用表：

- `exams`
- `exam_questions`
- `exam_submissions`
- `submission_answers`
- `submission_behavior_events`

### 9.6 阅卷与评分接口

- `/teacher/review/objective-score`
- `/teacher/review/ai-score`
- `/teacher/review/submit`

主要使用表：

- `exam_submissions`
- `submission_answers`
- `review_items`
- `review_logs`
- `ai_tasks`

### 9.7 学生分析与成长接口

- `/student/results/overview`
- `/student/analytics/knowledge-map`
- `/student/analytics/ability-profile`

主要使用表：

- `exam_submissions`
- `submission_answers`
- `student_profile_snapshots`
- `knowledge_mastery_snapshots`

### 9.8 AI 对话接口

- `/student/ai-chat/sessions/create`
- `/student/ai-chat/messages`
- `WS /ws/ai-chat/{session_id}`

主要使用表：

- `ai_chat_sessions`
- `ai_chat_messages`

### 9.9 学习计划接口

- `/student/study-plans/current`
- `/student/study-plans/generate`

主要使用表：

- `study_plans`
- `study_tasks`
- `ai_tasks`

### 9.10 报告中心接口

- `/reports`
- `/reports/generate`
- `/reports/export`

主要使用表：

- `reports`
- `ai_tasks`

## 10. 分析类字段的存储策略

对于 AI 分析结果和复杂报表，建议采用“关系字段 + JSON 快照”双轨存储：

1. 可筛选、可排序、可统计的核心字段单独建列。
2. 复杂结构化结果放入 JSON 字段保存快照。

例如：

- `submission_answers.ai_error_analysis`
- `exams.ai_evaluation_result`
- `reports.content_json`
- `student_profile_snapshots.profile_json`

这样既能保留灵活性，也能保留查询效率。

## 11. 索引优化建议

### 11.1 高频查询场景

重点优化以下查询：

1. 教师查看班级考试列表。
2. 学生获取待考考试与当前提交记录。
3. 教师查看某场考试的成绩分布与复核列表。
4. 学生查看错题集与知识点地图。
5. AI 任务轮询状态。

### 11.2 建议重点索引

- `exam_submissions(exam_id, class_id)`
- `exam_submissions(student_id, created_at)`
- `submission_answers(submission_id, is_correct)`
- `review_items(exam_id, review_status)`
- `ai_tasks(task_id)`
- `ai_tasks(resource_type, resource_id)`
- `reports(report_type, status)`
- `knowledge_mastery_snapshots(owner_type, owner_id, subject_id)`

## 12. 数据一致性建议

### 12.1 分数一致性

- `exam_submissions.total_score = objective_score + subjective_score`
- 成绩发布前应重新汇总一次 `submission_answers.score`

### 12.2 冗余字段一致性

- `classes.student_count` 建议通过事务或异步任务更新。
- 排名字段 `ranking_in_class` 建议在成绩发布后统一批量刷新。

### 12.3 AI 结果一致性

- AI 任务结果建议先写入 `ai_tasks.result_payload`。
- 核心业务表只在任务成功后写入正式字段。

## 13. 安全与审计建议

1. 用户密码必须使用安全哈希算法，例如 bcrypt 或 argon2。
2. 敏感报告下载地址建议采用签名 URL。
3. 教师评分行为建议保留 `review_logs` 审计记录。
4. AI 生成结果建议保留快照，避免后续模型变化影响历史数据解释。
5. 如后续涉及家长端，应单独设计数据权限模型。

## 14. 分阶段落地建议

### 14.1 第一阶段

优先实现最小可用链路：

- `users`
- `classes`
- `class_students`
- `subjects`
- `knowledge_points`
- `questions`
- `question_options`
- `question_knowledge_points`
- `exams`
- `exam_questions`
- `exam_classes`
- `exam_submissions`
- `submission_answers`

### 14.2 第二阶段

补全考试分析和阅卷：

- `submission_behavior_events`
- `review_items`
- `review_logs`
- `ai_tasks`

### 14.3 第三阶段

补全 AI 增强能力：

- `ai_chat_sessions`
- `ai_chat_messages`
- `study_plans`
- `study_tasks`
- `reports`
- `student_profile_snapshots`
- `class_analysis_snapshots`
- `knowledge_mastery_snapshots`

## 15. 建议的 SQLAlchemy 模块拆分

为了配合后端实现，建议模型文件按领域拆分：

- `models/user.py`
- `models/classroom.py`
- `models/question.py`
- `models/exam.py`
- `models/submission.py`
- `models/review.py`
- `models/ai_task.py`
- `models/chat.py`
- `models/study_plan.py`
- `models/report.py`
- `models/snapshot.py`

## 16. 总结

本数据库设计以“考试流程 + AI 诊断 + 成长追踪”为主线，既保证了传统考试系统的数据完整性，也为 AI 阅卷、学情分析、对话辅导、学习计划和报告中心预留了足够的扩展空间。数据库层的关键原则是：

1. 核心业务结构关系化。
2. AI 复杂输出快照化。
3. 高频查询字段索引化。
4. 历史分析结果可沉淀、可追踪、可复用。

这份文档可直接作为后续数据库建模、Alembic 迁移设计和 SQLAlchemy 实体定义的基础。
