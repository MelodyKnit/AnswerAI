# API 总览

本文档描述后端当前已实现的 API 约定。Base URL 沿用项目默认约定：

- 开发环境：`http://localhost:8000/api/v1`
- 生产环境：由部署环境决定，路径前缀保持 `/api/v1`

## 1. 认证约定

- 登录、注册、元数据接口可匿名访问。
- 其余 HTTP 接口均使用 Bearer Token。
- 教师专属接口通过服务端角色校验限制访问。
- 学生专属接口同样在服务端进行角色校验，不能仅依赖前端隐藏入口。

请求头示例：

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

## 2. 统一响应结构

所有 HTTP 接口都通过 `success_response(...)` 返回统一包装，业务数据位于 `data` 字段：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "req_xxx",
  "timestamp": "2026-03-16T10:00:00Z"
}
```

字段含义如下：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | integer | 业务状态码，`0` 表示成功 |
| message | string | 响应消息，部分写接口会返回更具体的成功说明 |
| data | object/array/null | 业务负载 |
| request_id | string | 请求追踪 ID |
| timestamp | string | 服务端响应时间 |

## 3. 分页规则

当前列表接口大多支持：

| 参数 | 类型 | 默认值 | 约束 |
| --- | --- | --- | --- |
| page | integer | 1 | 最小为 1 |
| page_size | integer | 20 | 一般限制在 1 到 100 |

常见返回结构：

```json
{
  "items": [],
  "total": 0
}
```

部分接口会额外返回 `page`、`page_size`、`total_pages`。

## 4. 时间与状态约定

- 时间字段统一使用 ISO 8601 字符串。
- 考试相关公开给前端的时间通常被序列化为 UTC 字符串，部分字段包含 `Z` 后缀。
- 提交状态常见值：`not_started`、`in_progress`、`submitted`、`reviewed`。
- 考试状态常见值：`draft`、`published`、`ongoing`、`finished`。
- AI 任务状态常见值：`pending`、`running`、`completed`、`failed`、`approved`、`rejected`、`consumed`。

## 5. 核心对象

### 5.1 User

```json
{
  "id": 1,
  "role": "student",
  "name": "张三",
  "username": "zhangsan01",
  "email": "student@example.com",
  "phone": "13800000000",
  "avatar_url": "/uploads/avatar.png",
  "school_name": "第一中学",
  "grade_name": "高一",
  "status": "active",
  "created_at": "2026-03-16T10:00:00+00:00"
}
```

### 5.2 Question

```json
{
  "id": 101,
  "subject": "数学",
  "type": "single_choice",
  "stem": "已知函数...",
  "options": [
    {"key": "A", "content": "选项 A"},
    {"key": "B", "content": "选项 B"}
  ],
  "answer": ["A"],
  "analysis": "参考解析",
  "score": 5,
  "difficulty": 0.6,
  "knowledge_points": [{"id": 12, "name": "函数性质"}],
  "ability_tags": ["审题能力", "计算能力"],
  "created_by": 21,
  "created_at": "2026-03-16T10:00:00+00:00"
}
```

### 5.3 Exam

```json
{
  "id": 1001,
  "title": "高一数学周测",
  "subject": "数学",
  "duration_minutes": 90,
  "total_score": 100,
  "status": "published",
  "start_time": "2026-03-16T08:00:00Z",
  "end_time": "2026-03-16T09:30:00Z",
  "instructions": "请独立完成作答",
  "allow_review": true,
  "random_question_order": false,
  "question_count": 20,
  "class_ids": [11, 12],
  "created_by": 21,
  "created_at": "2026-03-16T10:00:00+00:00"
}
```

### 5.4 Submission

```json
{
  "id": 9001,
  "exam_id": 1001,
  "student_id": 1,
  "status": "submitted",
  "started_at": "2026-03-16T08:03:00+00:00",
  "submitted_at": "2026-03-16T09:01:00+00:00",
  "deadline_at": "2026-03-16T09:30:00+00:00",
  "objective_score": 58,
  "subjective_score": 20,
  "total_score": 78,
  "correct_rate": 0.74,
  "ranking_in_class": 8
}
```

### 5.5 ReviewItem

```json
{
  "id": 3001,
  "exam_id": 1001,
  "submission_id": 9001,
  "question_id": 101,
  "student_id": 1,
  "ai_suggest_score": 6,
  "final_score": 8,
  "review_status": "reviewed"
}
```

### 5.6 AITask

```json
{
  "task_id": "task_xxx",
  "type": "study_plan_generate",
  "status": "completed",
  "progress": 100,
  "resource_type": "submission",
  "resource_id": 9001
}
```

### 5.7 Report

```json
{
  "id": 501,
  "report_type": "exam",
  "title": "高一数学周测报告",
  "status": "ready",
  "summary": "本次考试整体完成较好",
  "file_url": "/exports/reports/501.json"
}
```

## 6. 模块导航

- [docs/api/auth-meta.md](docs/api/auth-meta.md)
- [docs/api/student.md](docs/api/student.md)
- [docs/api/teacher-classes-questions.md](docs/api/teacher-classes-questions.md)
- [docs/api/teacher-exams-review.md](docs/api/teacher-exams-review.md)
- [docs/api/support.md](docs/api/support.md)
