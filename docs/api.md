# AI考试答题平台 API 文档

本文档基于 README 中定义的功能模块整理，接口风格统一为 GET、POST 和 WebSocket 三类，便于前后端实现一致的调用规范。

## 1. 总体约定

### 1.1 Base URL

- 开发环境：http://localhost:8000/api/v1
- 生产环境：https://api.example.com/api/v1

### 1.2 认证方式

- 采用 Bearer Token 鉴权。
- 除登录、注册、公开元数据接口外，其余接口都需要在 Header 中传入 Authorization。

请求头示例：

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### 1.3 接口方法规范

- GET：用于获取数据，不修改服务端状态。
- POST：用于创建、更新、删除、触发动作、执行分析等所有写操作。
- WebSocket：用于考试过程实时通信、AI 对话流式输出、异步任务进度推送。

### 1.4 统一响应结构

所有 HTTP 接口统一返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "req_20260313_0001",
  "timestamp": "2026-03-13T10:00:00Z"
}
```

返回字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | integer | 是 | 业务状态码，0 表示成功 |
| message | string | 是 | 业务说明信息 |
| data | object 或 array 或 null | 是 | 实际业务数据 |
| request_id | string | 是 | 请求追踪 ID |
| timestamp | string | 是 | 服务端响应时间，ISO 8601 |

### 1.5 分页结构

列表接口统一支持分页参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| page | integer | 否 | 1 | 页码，从 1 开始 |
| page_size | integer | 否 | 20 | 每页数量，建议最大 100 |

分页返回结构：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 100,
  "total_pages": 5
}
```

### 1.6 通用状态枚举

用户角色：

- student：学生
- teacher：教师
- admin：管理员

考试状态：

- draft：草稿
- published：已发布
- ongoing：进行中
- finished：已结束
- archived：已归档

任务状态：

- pending：等待中
- running：执行中
- success：执行成功
- failed：执行失败

提交状态：

- not_started：未开始
- in_progress：作答中
- submitted：已提交
- reviewed：已评阅

## 2. 核心数据结构

### 2.1 User 对象

```json
{
  "id": 1,
  "role": "student",
  "name": "张三",
  "email": "student@example.com",
  "phone": "13800000000",
  "avatar_url": "https://cdn.example.com/avatar.png",
  "school_name": "第一中学",
  "grade_name": "高一",
  "class_id": 11,
  "class_name": "高一1班",
  "teacher_id": 21,
  "teacher_name": "李老师",
  "status": "active",
  "created_at": "2026-03-13T10:00:00Z"
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 用户 ID |
| role | string | 用户角色 |
| name | string | 用户姓名 |
| email | string | 邮箱 |
| phone | string | 手机号 |
| avatar_url | string | 头像地址 |
| school_name | string | 学校名称 |
| grade_name | string | 年级名称 |
| class_id | integer | 班级 ID |
| class_name | string | 班级名称 |
| teacher_id | integer | 对应教师 ID |
| teacher_name | string | 对应教师姓名 |
| status | string | 账号状态 |
| created_at | string | 创建时间 |

### 2.2 Class 对象

```json
{
  "id": 11,
  "name": "高一1班",
  "grade_name": "高一",
  "subject": "数学",
  "teacher_id": 21,
  "student_count": 45,
  "invite_code": "CLS-A001",
  "created_at": "2026-03-13T10:00:00Z"
}
```

### 2.3 KnowledgePoint 对象

```json
{
  "id": 100,
  "name": "函数性质",
  "subject": "数学",
  "parent_id": 10,
  "level": 2,
  "path": "数学/函数/函数性质"
}
```

### 2.4 Question 对象

```json
{
  "id": 101,
  "subject": "数学",
  "type": "single_choice",
  "stem": "已知函数 f(x)=...",
  "options": [
    {"key": "A", "content": "选项A"},
    {"key": "B", "content": "选项B"}
  ],
  "answer": ["A"],
  "analysis": "参考解析内容",
  "score": 5,
  "difficulty": 0.65,
  "knowledge_points": [
    {"id": 100, "name": "函数性质"}
  ],
  "ability_tags": ["审题能力", "计算能力"],
  "created_by": 21,
  "created_at": "2026-03-13T10:00:00Z"
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 题目 ID |
| subject | string | 学科 |
| type | string | 题型，如 single_choice、multiple_choice、judge、blank、essay |
| stem | string | 题干内容 |
| options | array | 选项列表，非选择题可为空数组 |
| answer | array 或 string | 标准答案 |
| analysis | string | 参考解析 |
| score | number | 题目分值 |
| difficulty | number | 难度系数，0 到 1 |
| knowledge_points | array | 知识点列表 |
| ability_tags | array | 能力标签 |
| created_by | integer | 创建教师 ID |
| created_at | string | 创建时间 |

### 2.5 Exam 对象

```json
{
  "id": 1001,
  "title": "高一数学周测",
  "subject": "数学",
  "duration_minutes": 90,
  "total_score": 100,
  "status": "published",
  "start_time": "2026-03-13T08:00:00Z",
  "end_time": "2026-03-13T10:00:00Z",
  "instructions": "请独立完成作答",
  "allow_review": true,
  "random_question_order": false,
  "question_count": 20,
  "class_ids": [11, 12],
  "created_by": 21,
  "created_at": "2026-03-13T10:00:00Z"
}
```

### 2.6 Submission 对象

```json
{
  "id": 9001,
  "exam_id": 1001,
  "student_id": 1,
  "status": "submitted",
  "started_at": "2026-03-13T08:05:00Z",
  "submitted_at": "2026-03-13T09:21:00Z",
  "deadline_at": "2026-03-13T09:35:00Z",
  "objective_score": 58,
  "subjective_score": 20,
  "total_score": 78,
  "correct_rate": 0.74,
  "ranking_in_class": 8
}
```

### 2.7 AITask 对象

```json
{
  "task_id": "task_123456",
  "type": "exam_analysis",
  "status": "running",
  "progress": 60,
  "resource_type": "submission",
  "resource_id": 9001,
  "result": null,
  "error_message": null,
  "created_at": "2026-03-13T10:00:00Z",
  "updated_at": "2026-03-13T10:03:00Z"
}
```

### 2.8 Report 对象

```json
{
  "id": 5001,
  "report_type": "class",
  "title": "高一1班数学周测分析报告",
  "exam_id": 1001,
  "class_id": 11,
  "student_id": null,
  "status": "ready",
  "summary": "班级基础题表现稳定，综合题失分明显。",
  "file_url": "https://cdn.example.com/reports/5001.pdf",
  "created_at": "2026-03-13T10:00:00Z"
}
```

## 3. 认证与账户接口

### 3.1 用户注册

接口地址：POST /auth/register

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| role | string | 是 | 用户角色，student 或 teacher |
| name | string | 是 | 用户姓名 |
| email | string | 是 | 邮箱，需唯一 |
| password | string | 是 | 登录密码，建议 8 位以上 |
| phone | string | 否 | 手机号 |
| school_name | string | 否 | 学校名称 |
| grade_name | string | 否 | 年级名称，学生建议填写 |
| teacher_invite_code | string | 否 | 学生绑定教师的邀请码 |
| class_code | string | 否 | 学生绑定班级的邀请码 |

请求示例：

```json
{
  "role": "student",
  "name": "张三",
  "email": "student@example.com",
  "password": "Password123",
  "phone": "13800000000",
  "school_name": "第一中学",
  "grade_name": "高一",
  "teacher_invite_code": "TCH-001",
  "class_code": "CLS-A001"
}
```

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| access_token | string | 登录令牌 |
| token_type | string | 固定为 bearer |
| user | object | 用户信息，结构见 User 对象 |

返回示例：

```json
{
  "code": 0,
  "message": "register success",
  "data": {
    "access_token": "jwt_token",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "role": "student",
      "name": "张三",
      "email": "student@example.com"
    }
  },
  "request_id": "req_001",
  "timestamp": "2026-03-13T10:00:00Z"
}
```

### 3.2 用户登录

接口地址：POST /auth/login

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| email | string | 是 | 登录邮箱 |
| password | string | 是 | 登录密码 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| access_token | string | 登录令牌 |
| token_type | string | 固定为 bearer |
| expires_in | integer | 过期秒数 |
| user | object | 当前登录用户 |

### 3.3 获取当前用户信息

接口地址：GET /auth/me

请求参数：无

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| user | object | 当前用户完整信息 |

### 3.4 更新个人资料

接口地址：POST /users/profile/update

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| name | string | 否 | 用户姓名 |
| phone | string | 否 | 手机号 |
| avatar_url | string | 否 | 头像地址 |
| school_name | string | 否 | 学校名称 |
| grade_name | string | 否 | 年级名称 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| user | object | 更新后的用户信息 |

### 3.5 修改密码

接口地址：POST /users/password/change

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| old_password | string | 是 | 原密码 |
| new_password | string | 是 | 新密码 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| success | boolean | 是否修改成功 |

## 4. 基础元数据接口

### 4.1 获取学科列表

接口地址：GET /meta/subjects

请求参数：无

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 学科列表，每项含 code、name |

### 4.2 获取年级列表

接口地址：GET /meta/grades

请求参数：无

### 4.3 获取题型列表

接口地址：GET /meta/question-types

请求参数：无

### 4.4 获取知识点树

接口地址：GET /meta/knowledge-points/tree

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 是 | 学科名称 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 知识点树结构 |

## 5. 教师班级与学生管理接口

### 5.1 获取教师班级列表

接口地址：GET /teacher/classes

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 班级列表，每项为 Class 对象 |
| page | integer | 页码 |
| page_size | integer | 每页数量 |
| total | integer | 总记录数 |
| total_pages | integer | 总页数 |

### 5.2 创建班级

接口地址：POST /teacher/classes/create

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| name | string | 是 | 班级名称 |
| grade_name | string | 是 | 年级名称 |
| subject | string | 是 | 学科 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| class | object | 新建班级信息 |

### 5.3 获取班级详情

接口地址：GET /teacher/classes/detail

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| class_id | integer | 是 | 班级 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| class | object | 班级信息 |
| recent_exam_count | integer | 近期考试数量 |
| student_count | integer | 学生人数 |

### 5.4 获取班级学生列表

接口地址：GET /teacher/classes/students

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| class_id | integer | 是 | 班级 ID |
| keyword | string | 否 | 学生姓名关键字 |
| risk_level | string | 否 | 风险等级，如 high、medium、low |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 学生列表，包含基础信息与风险摘要 |
| total | integer | 总数 |

### 5.5 获取学生详情

接口地址：GET /teacher/students/detail

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| student_id | integer | 是 | 学生 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| student | object | 学生基础信息 |
| class | object | 所属班级 |
| latest_summary | object | 最近学习摘要 |

## 6. 教师题库与出题接口

### 6.1 获取题库列表

接口地址：GET /teacher/questions

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 否 | 学科 |
| type | string | 否 | 题型 |
| difficulty_min | number | 否 | 最小难度 |
| difficulty_max | number | 否 | 最大难度 |
| knowledge_point_id | integer | 否 | 知识点 ID |
| keyword | string | 否 | 题干关键字 |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 题目列表，每项为 Question 对象 |
| total | integer | 总数 |

### 6.2 创建题目

接口地址：POST /teacher/questions/create

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 是 | 学科 |
| type | string | 是 | 题型 |
| stem | string | 是 | 题干 |
| options | array | 否 | 选择题选项列表 |
| answer | array 或 string | 是 | 标准答案 |
| analysis | string | 否 | 解析 |
| score | number | 是 | 分值 |
| difficulty | number | 否 | 难度系数 |
| knowledge_point_ids | array | 否 | 知识点 ID 列表 |
| ability_tags | array | 否 | 能力标签列表 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| question | object | 创建后的题目信息 |

### 6.3 更新题目

接口地址：POST /teacher/questions/update

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| question_id | integer | 是 | 题目 ID |
| subject | string | 否 | 学科 |
| type | string | 否 | 题型 |
| stem | string | 否 | 题干 |
| options | array | 否 | 选项列表 |
| answer | array 或 string | 否 | 标准答案 |
| analysis | string | 否 | 解析 |
| score | number | 否 | 分值 |
| difficulty | number | 否 | 难度系数 |
| knowledge_point_ids | array | 否 | 知识点 ID 列表 |
| ability_tags | array | 否 | 能力标签 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| question | object | 更新后的题目信息 |

### 6.4 删除题目

接口地址：POST /teacher/questions/delete

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| question_id | integer | 是 | 题目 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| success | boolean | 是否删除成功 |

### 6.5 批量导入题目

接口地址：POST /teacher/questions/import

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file_url | string | 否 | 上传后的文件地址 |
| import_type | string | 是 | excel、csv、json |
| subject | string | 是 | 学科 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| import_count | integer | 导入成功数量 |
| failed_count | integer | 导入失败数量 |
| errors | array | 失败明细 |

### 6.6 AI 辅助出题

接口地址：POST /teacher/questions/ai-generate

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 是 | 学科 |
| grade_name | string | 是 | 年级 |
| question_type | string | 是 | 题型 |
| knowledge_points | array | 是 | 知识点名称列表 |
| difficulty | number | 否 | 目标难度 |
| count | integer | 否 | 生成数量 |
| with_analysis | boolean | 否 | 是否生成解析 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| questions | array | AI 生成的题目草案列表 |
| task_id | string | 若异步生成则返回任务 ID |

### 6.7 AI 题目质量检查

接口地址：POST /teacher/questions/ai-review

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| question_id | integer | 是 | 题目 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| review | object | 质量检查结果 |
| review.ambiguity_risk | string | 歧义风险 |
| review.option_quality | string | 选项质量 |
| review.answer_consistency | string | 答案一致性 |
| review.difficulty_estimation | number | 难度预估 |
| review.suggestions | array | 优化建议列表 |

## 7. 教师考试管理接口

### 7.1 创建考试

接口地址：POST /teacher/exams/create

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| title | string | 是 | 考试名称 |
| subject | string | 是 | 学科 |
| duration_minutes | integer | 是 | 考试时长，分钟 |
| start_time | string | 是 | 开始时间 |
| end_time | string | 是 | 结束时间 |
| instructions | string | 否 | 考试说明 |
| allow_review | boolean | 否 | 是否允许回看 |
| random_question_order | boolean | 否 | 是否随机题序 |
| class_ids | array | 是 | 参与班级 ID 列表 |
| question_items | array | 是 | 题目列表，包含 question_id、score、order_no |

请求约束补充：

- `subject` 必须是系统中已存在的学科名称，否则返回 `404 Subject not found`。
- `question_items` 可以为空数组，此时创建的考试总分为 `0`，后续可通过更新考试补充题目。
- 前端若收到 `422`，应直接展示后端返回的 `detail` 字段，不应替换为固定文案。

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| exam | object | 考试信息 |

### 7.2 获取考试列表

接口地址：GET /teacher/exams

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| status | string | 否 | 考试状态 |
| subject | string | 否 | 学科 |
| class_id | integer | 否 | 班级 ID |
| keyword | string | 否 | 关键字 |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 考试列表，每项为 Exam 对象 |
| total | integer | 总数 |

### 7.3 获取考试详情

接口地址：GET /teacher/exams/detail

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| exam | object | 考试信息 |
| question_items | array | 试卷题目列表 |
| classes | array | 参与班级列表 |

### 7.4 更新考试

接口地址：POST /teacher/exams/update

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| title | string | 否 | 考试名称 |
| duration_minutes | integer | 否 | 时长 |
| start_time | string | 否 | 开始时间 |
| end_time | string | 否 | 结束时间 |
| instructions | string | 否 | 说明 |
| allow_review | boolean | 否 | 是否允许回看 |
| random_question_order | boolean | 否 | 是否随机题序 |
| class_ids | array | 否 | 班级列表 |
| question_items | array | 否 | 题目列表 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| exam | object | 更新后的考试信息 |

### 7.5 发布考试

接口地址：POST /teacher/exams/publish

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| exam_id | integer | 考试 ID |
| status | string | 发布后的状态 |

### 7.6 暂停考试

接口地址：POST /teacher/exams/pause

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

### 7.7 结束考试

接口地址：POST /teacher/exams/finish

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

### 7.8 删除考试

接口地址：POST /teacher/exams/delete

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

### 7.9 获取考试洞察分析

接口地址：GET /teacher/exams/insights

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| progress | object | 作答进度信息 |
| progress.submitted_count | integer | 已开始/已提交人数 |
| progress.target_count | integer | 班级目标人数 |
| progress.completion_rate | number | 完成率，0-1 |
| learning | object | 学习指标 |
| learning.avg_duration_minutes | number | 平均作答时长（分钟） |
| learning.avg_score | number | 平均得分 |
| learning.overall_wrong_rate | number | 整体错误率，0-1 |
| top_wrong_questions | array | 高错题列表（最多 3 条） |
| top_wrong_questions[].question_id | integer | 题目 ID |
| top_wrong_questions[].stem | string | 题干 |
| top_wrong_questions[].answer_count | integer | 作答人次 |
| top_wrong_questions[].wrong_count | integer | 错误人次 |
| top_wrong_questions[].wrong_rate | number | 错误率，0-1 |
| top_wrong_questions[].avg_spent_seconds | number | 平均耗时（秒） |
| ai_summary | object | AI 规则解读摘要 |
| ai_summary.easy_mistakes | array | 易错点描述列表 |
| ai_summary.teaching_suggestions | array | 教学建议列表 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| success | boolean | 是否删除成功 |

### 7.9 AI 预估试卷质量

接口地址：POST /teacher/exams/ai-evaluate

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| evaluation | object | 评估结果 |
| evaluation.difficulty | number | 难度估计 |
| evaluation.discrimination | number | 区分度估计 |
| evaluation.coverage_score | number | 知识点覆盖度 |
| evaluation.structure_comments | array | 结构评价 |
| evaluation.estimated_duration_minutes | integer | 预计平均完成时长 |

## 8. 学生考试流程接口

### 8.1 获取待考考试列表

接口地址：GET /student/exams

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| status | string | 否 | upcoming、ongoing、finished |
| subject | string | 否 | 学科 |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 考试列表 |
| total | integer | 总数 |

### 8.2 获取考试详情

接口地址：GET /student/exams/detail

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| exam | object | 考试信息 |
| can_start | boolean | 当前是否可开始 |
| rules | object | 考试规则 |

### 8.3 开始考试

接口地址：POST /student/exams/start

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| submission | object | 作答提交对象 |
| paper_token | string | 拉取试卷内容的临时令牌 |

### 8.4 获取试卷内容

接口地址：GET /student/exams/paper

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 作答 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| exam | object | 考试信息 |
| questions | array | 试题列表，不包含标准答案 |
| remaining_seconds | integer | 剩余时间 |

### 8.5 保存单题答案

接口地址：POST /student/exams/answer/save

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 作答 ID |
| question_id | integer | 是 | 题目 ID |
| answer | array 或 string | 否 | 题目答案 |
| answer_text | string | 否 | 主观题文本答案 |
| spent_seconds | integer | 否 | 当前题已花费秒数 |
| mark_difficult | boolean | 否 | 是否标记为疑难题 |
| favorite | boolean | 否 | 是否收藏 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| saved | boolean | 是否保存成功 |
| answer_version | integer | 当前答案版本号 |
| saved_at | string | 保存时间 |

### 8.6 批量保存答案

接口地址：POST /student/exams/answers/save-batch

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 作答 ID |
| answers | array | 是 | 批量答案列表 |

answers 子项结构：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| question_id | integer | 是 | 题目 ID |
| answer | array 或 string | 否 | 答案 |
| answer_text | string | 否 | 主观题答案 |
| spent_seconds | integer | 否 | 用时 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| saved_count | integer | 成功保存数量 |

### 8.7 上报答题行为事件

接口地址：POST /student/exams/behavior/report

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 作答 ID |
| events | array | 是 | 行为事件列表 |

events 子项结构：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| question_id | integer | 否 | 关联题目 ID |
| event_type | string | 是 | 事件类型，如 focus、blur、switch、change_answer |
| occurred_at | string | 是 | 发生时间 |
| payload | object | 否 | 扩展字段 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| received | boolean | 是否接收成功 |
| event_count | integer | 接收事件数量 |

### 8.8 提交前检查

接口地址：GET /student/exams/pre-submit-check

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 作答 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| unanswered_question_ids | array | 未答题 ID 列表 |
| marked_question_ids | array | 已标记题目 ID 列表 |
| subjective_warnings | array | 主观题完整性提醒 |
| ai_reminders | array | AI 发现的遗漏提醒 |

### 8.9 提交试卷

接口地址：POST /student/exams/submit

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 作答 ID |
| confirm_submit | boolean | 是 | 是否确认提交 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| submission | object | 提交后的作答信息 |
| triggered_tasks | array | 已触发的 AI 任务列表 |

## 9. 阅卷与评分接口

### 9.1 获取客观题自动判分结果

接口地址：GET /teacher/review/objective-score

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 作答 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| submission_id | integer | 作答 ID |
| objective_score | number | 客观题得分 |
| question_scores | array | 每题得分明细 |

### 9.2 触发主观题 AI 初评

接口地址：POST /teacher/review/ai-score

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 作答 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| task_id | string | AI 初评任务 ID |
| status | string | 当前任务状态 |

### 9.3 获取待复核列表

接口地址：GET /teacher/review/items

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| review_status | string | 否 | pending、reviewed |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 待复核项目列表 |
| total | integer | 总数 |

### 9.4 提交教师复核结果

接口地址：POST /teacher/review/submit

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| review_item_id | integer | 是 | 复核项 ID |
| final_score | number | 是 | 最终得分 |
| review_comment | string | 否 | 教师评语 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| review_item_id | integer | 复核项 ID |
| status | string | 复核状态 |

### 9.5 发布成绩

接口地址：POST /teacher/review/publish-results

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| exam_id | integer | 考试 ID |
| published | boolean | 是否发布成功 |

## 10. 学生工作台与结果分析接口

### 10.1 学生工作台总览

接口地址：GET /student/dashboard/overview

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 否 | 学科筛选 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| upcoming_exam_count | integer | 待参加考试数量 |
| recent_exams | array | 近期考试列表 |
| latest_result_summary | object | 最近一次成绩摘要 |
| ai_reminders | array | AI 学习提醒列表 |
| ability_profile_summary | object | 能力画像摘要 |
| recommended_tasks | array | 推荐学习任务 |

### 10.2 获取成绩总览

接口地址：GET /student/results/overview

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| submission | object | 本次提交信息 |
| score_summary | object | 分数汇总 |
| ranking_summary | object | 排名与班级对比 |
| type_score_distribution | array | 题型得分分布 |
| ai_summary | string | AI 总结 |
| risk_alerts | array | 风险提醒 |

### 10.3 获取题目结果列表

接口地址：GET /student/results/questions

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| is_wrong | boolean | 否 | 是否只看错题 |
| question_type | string | 否 | 题型 |
| knowledge_point_id | integer | 否 | 知识点 ID |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 题目结果列表 |
| total | integer | 总数 |

### 10.4 获取错题详情

接口地址：GET /student/results/question-detail

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| question_id | integer | 是 | 题目 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| question | object | 题目信息 |
| student_answer | object | 学生答案 |
| standard_answer | object | 标准答案 |
| score_detail | object | 得分详情 |
| ai_error_analysis | object | AI 错因分析 |
| related_knowledge_points | array | 相关知识点 |
| similar_questions | array | 相似题推荐 |

### 10.5 获取知识薄弱点地图

接口地址：GET /student/analytics/knowledge-map

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 否 | 学科 |
| exam_id | integer | 否 | 单次考试 ID |
| time_range | string | 否 | 时间范围，如 30d、90d |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| nodes | array | 知识点节点 |
| links | array | 关联边 |
| weak_points | array | 薄弱点列表 |

### 10.6 获取能力画像

接口地址：GET /student/analytics/ability-profile

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 否 | 学科 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| dimensions | array | 维度列表 |
| scores | array | 各维度得分 |
| ai_comment | string | AI 画像点评 |

### 10.7 获取成长趋势

接口地址：GET /student/analytics/growth-trend

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 否 | 学科 |
| time_range | string | 否 | 时间范围 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| exam_points | array | 考试成绩趋势点 |
| knowledge_trends | array | 知识点变化趋势 |
| mistake_type_trends | array | 失误类型趋势 |

### 10.8 获取错题集

接口地址：GET /student/wrong-questions

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 否 | 学科 |
| knowledge_point_id | integer | 否 | 知识点 ID |
| source_exam_id | integer | 否 | 来源考试 ID |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 错题列表 |
| total | integer | 总数 |

## 11. AI 学习计划接口

### 11.1 获取当前学习计划

接口地址：GET /student/study-plans/current

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 否 | 学科 |
| exam_id | integer | 否 | 来源考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| plan | object | 学习计划 |
| tasks | array | 学习任务列表 |

### 11.2 生成或刷新学习计划

接口地址：POST /student/study-plans/generate

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 是 | 学科 |
| exam_id | integer | 否 | 参考考试 ID |
| plan_type | string | 否 | daily、weekly、sprint |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| task_id | string | 生成任务 ID |
| status | string | 任务状态 |

### 11.3 获取学习任务列表

接口地址：GET /student/study-tasks

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| status | string | 否 | pending、completed |
| subject | string | 否 | 学科 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 学习任务列表 |

### 11.4 更新学习任务状态

接口地址：POST /student/study-tasks/update

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| task_id | integer | 是 | 学习任务 ID |
| status | string | 是 | pending、completed |
| feedback | string | 否 | 完成反馈 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| task | object | 更新后的任务信息 |

## 12. 教师工作台与分析接口

### 12.1 获取教师工作台总览

接口地址：GET /teacher/dashboard/overview

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 否 | 学科 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| exam_count | integer | 考试总数 |
| pending_review_count | integer | 待批改数量 |
| risk_student_count | integer | 风险学生数量 |
| avg_score_trend | array | 平均分趋势 |
| ai_class_summary | string | AI 班级摘要 |

### 12.2 获取班级成绩分析

接口地址：GET /teacher/analytics/class-exam

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| class_id | integer | 是 | 班级 ID |
| exam_id | integer | 是 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| score_distribution | array | 分数分布 |
| pass_rate | number | 及格率 |
| excellent_rate | number | 优秀率 |
| question_accuracy | array | 题目正确率 |
| knowledge_mastery | array | 知识点掌握率 |
| avg_spent_seconds | integer | 平均用时 |
| ai_conclusion | string | AI 结论 |

### 12.3 获取班级知识点分析

接口地址：GET /teacher/analytics/class-knowledge

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| class_id | integer | 是 | 班级 ID |
| subject | string | 否 | 学科 |
| exam_id | integer | 否 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 知识点分析结果 |

### 12.4 获取班级题型分析

接口地址：GET /teacher/analytics/class-question-types

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| class_id | integer | 是 | 班级 ID |
| exam_id | integer | 否 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 各题型表现分析 |

### 12.5 获取学生画像

接口地址：GET /teacher/analytics/student-profile

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| student_id | integer | 是 | 学生 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| student | object | 学生信息 |
| score_trend | array | 历次成绩趋势 |
| weak_points | array | 薄弱点 |
| mistake_distribution | array | 失误类型分布 |
| ability_radar | array | 能力雷达数据 |
| ai_profile_summary | string | AI 学生画像总结 |

### 12.6 学生与班级对比分析

接口地址：GET /teacher/analytics/student-vs-class

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| student_id | integer | 是 | 学生 ID |
| class_id | integer | 是 | 班级 ID |
| exam_id | integer | 否 | 考试 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| compare_dimensions | array | 对比维度 |
| student_scores | array | 学生数据 |
| class_avg_scores | array | 班级平均数据 |

### 12.7 获取教学洞察

接口地址：GET /teacher/analytics/teaching-insights

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| class_id | integer | 否 | 班级 ID |
| exam_id | integer | 否 | 考试 ID |
| subject | string | 否 | 学科 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| common_issues | array | 共性问题清单 |
| cause_analysis | array | 原因判断 |
| suggested_knowledge_points | array | 建议补讲知识点 |
| suggested_exercises | array | 建议课堂练习 |
| key_students | array | 重点关注学生 |
| ai_summary | string | AI 教学洞察总结 |

## 13. AI 报告中心接口

### 13.1 获取报告列表

接口地址：GET /reports

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| report_type | string | 否 | exam、class、student、knowledge_topic |
| exam_id | integer | 否 | 考试 ID |
| class_id | integer | 否 | 班级 ID |
| student_id | integer | 否 | 学生 ID |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 报告列表，每项为 Report 对象 |
| total | integer | 总数 |

### 13.2 获取报告详情

接口地址：GET /reports/detail

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| report_id | integer | 是 | 报告 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| report | object | 报告对象 |
| sections | array | 报告章节内容 |

### 13.3 触发生成报告

接口地址：POST /reports/generate

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| report_type | string | 是 | exam、class、student、knowledge_topic |
| exam_id | integer | 否 | 考试 ID |
| class_id | integer | 否 | 班级 ID |
| student_id | integer | 否 | 学生 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| task_id | string | 报告生成任务 ID |
| status | string | 任务状态 |

### 13.4 导出报告

接口地址：POST /reports/export

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| report_id | integer | 是 | 报告 ID |
| format | string | 是 | pdf、docx |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| file_url | string | 导出文件地址 |

### 13.5 分享报告

接口地址：POST /reports/share

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| report_id | integer | 是 | 报告 ID |
| target_type | string | 是 | student、parent、teacher_group |
| target_ids | array | 是 | 目标用户 ID 列表 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| success | boolean | 是否分享成功 |

## 14. AI 任务接口

### 14.1 查询单个任务状态

接口地址：GET /ai/tasks/status

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| task_id | string | 是 | 任务 ID |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| task | object | 任务对象 |

### 14.2 批量查询任务状态

接口地址：POST /ai/tasks/status/batch

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| task_ids | array | 是 | 任务 ID 列表 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| tasks | array | 任务状态列表 |

## 15. WebSocket 接口

### 15.1 考试实时连接

连接地址：WS /ws/exams/{exam_id}/submissions/{submission_id}

用途：

- 考试剩余时间实时同步
- 自动保存状态回执
- 强制交卷通知
- 监考或异常提醒推送

连接参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| token | string | 是 | Bearer Token，可通过 query 或 header 传入 |
| exam_id | integer | 是 | 考试 ID |
| submission_id | integer | 是 | 作答 ID |

客户端发送消息结构：

```json
{
  "event": "ping",
  "data": {
    "client_time": "2026-03-13T08:10:00Z"
  }
}
```

服务端推送消息结构：

```json
{
  "event": "countdown",
  "data": {
    "remaining_seconds": 3200,
    "server_time": "2026-03-13T08:10:01Z"
  }
}
```

常见事件：

| event | 方向 | 说明 |
| --- | --- | --- |
| ping | 客户端到服务端 | 心跳 |
| pong | 服务端到客户端 | 心跳响应 |
| countdown | 服务端到客户端 | 剩余时间推送 |
| autosave_ack | 服务端到客户端 | 自动保存确认 |
| force_submit | 服务端到客户端 | 强制交卷 |
| warning | 服务端到客户端 | 风险提醒 |

### 15.2 AI 对话流式连接

连接地址：WS /ws/ai-chat/{session_id}

用途：

- AI 连续输出讲解内容
- 按段返回推理结果、相似题建议和追问建议

连接参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| token | string | 是 | 登录令牌 |
| session_id | string | 是 | 会话 ID |

客户端发送消息：

```json
{
  "event": "chat_message",
  "data": {
    "message": "为什么我第二步推导错了？"
  }
}
```

服务端流式推送：

```json
{
  "event": "chat_chunk",
  "data": {
    "chunk": "因为你在这一步把定义域条件忽略了，",
    "finished": false
  }
}
```

最终完成消息：

```json
{
  "event": "chat_done",
  "data": {
    "message_id": "msg_001",
    "full_text": "完整回复内容",
    "related_knowledge_points": ["函数定义域"],
    "suggested_questions": ["是否需要我给你出一道同类型题目？"]
  }
}
```

### 15.3 AI 任务进度推送

连接地址：WS /ws/ai-tasks

用途：

- 前端统一订阅多个任务的处理进度
- 用于报告生成、AI 学习计划、主观题 AI 初评等场景

客户端订阅消息：

```json
{
  "event": "subscribe",
  "data": {
    "task_ids": ["task_001", "task_002"]
  }
}
```

服务端推送消息：

```json
{
  "event": "task_progress",
  "data": {
    "task_id": "task_001",
    "status": "running",
    "progress": 70,
    "message": "正在生成错因分析"
  }
}
```

## 16. AI 对话 HTTP 接口

### 16.1 创建 AI 对话会话

接口地址：POST /student/ai-chat/sessions/create

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| exam_id | integer | 是 | 考试 ID |
| question_id | integer | 否 | 题目 ID |
| mode | string | 是 | wrong_question_tutor、knowledge_tutor、practice_tutor |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| session_id | string | 会话 ID |
| websocket_url | string | 对应 WebSocket 地址 |

### 16.2 获取会话消息列表

接口地址：GET /student/ai-chat/messages

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| session_id | string | 是 | 会话 ID |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | array | 对话消息列表 |
| total | integer | 总数 |

### 16.3 生成相似题

接口地址：POST /student/ai-chat/generate-similar-question

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| session_id | string | 是 | 会话 ID |
| count | integer | 否 | 生成数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| task_id | string | 任务 ID |

### 16.4 生成即时小测

接口地址：POST /student/ai-chat/generate-quiz

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| session_id | string | 是 | 会话 ID |
| question_count | integer | 否 | 小测题目数量 |

返回参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| quiz | object | 小测信息 |
| questions | array | 小测题目 |

## 17. 推荐状态码与错误码

### 17.1 HTTP 状态码

| 状态码 | 说明 |
| --- | --- |
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未登录或登录失效 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 参数校验失败 |
| 500 | 服务器内部错误 |

### 17.2 业务错误码

| 错误码 | 说明 |
| --- | --- |
| 10001 | 账号或密码错误 |
| 10002 | 用户不存在 |
| 10003 | 角色不匹配 |
| 20001 | 考试未开始 |
| 20002 | 考试已截止 |
| 20003 | 试卷已提交，不允许重复提交 |
| 30001 | 阅卷任务尚未完成 |
| 30002 | AI 分析任务失败 |
| 40001 | 无权访问该班级 |
| 40002 | 无权访问该学生数据 |

## 18. 系统基建/上传接口

### 18.1 上传图片

**接口路径**: `POST /upload/image`

**鉴权**: 需要 `Bearer Token`，并且具备 `teacher` 角色（目前主要供教师侧题库及封面使用）。

**说明**: 上传单张图片（如 `.jpg, .png, .webp, .gif`），大小限制 8MB 内。返回可供公开访问的相对 URL。

**请求类型**: `multipart/form-data`

| 字段名称 | 类型 | 必填 | 默认项/说明 |
| --- | --- | --- | --- |
| file | file | 是 | 二进制图片文件内容 |

**成功响应示例**:

```json
{
  "code": 0,
  "data": {
    "file_name": "xxxxxx.png",
    "content_type": "image/png",
    "size": 102400,
    "url": "/uploads/xxxxxx.png"
  },
  "message": "upload success"
}
```

## 19. 设计说明

### 19.1 为什么统一使用 GET 和 POST

- 便于前端、网关和鉴权层统一处理。
- 降低复杂客户端对 PUT、DELETE 的兼容性问题。
- 对 AI 任务、评分操作、报告导出等动作型接口更直观。

### 19.2 为什么引入 WebSocket

- 考试剩余时间、自动保存确认、强制交卷更适合实时推送。
- AI 对话需要流式输出，WebSocket 体验优于轮询。
- AI 任务进度变化频繁，实时推送比轮询更高效。

### 19.3 后续可继续补充的内容

- 每个接口的完整响应示例
- OpenAPI 3.0 YAML 或 JSON 规范文件
- 数据库表结构设计文档
- FastAPI 路由、Schema、Service 对应关系说明
## 学生端分析与档案接口 (新增)

### 获取拥有的知识图谱数据
*   **Endpoint:** `GET /student/knowledge-map`
*   **Tags:** `Student`
*   **Query Parameters:**
    *   `subject` (optional, string): 学科筛选 (如: 数学)
*   **Response:**
    *   `200 OK`: 返回知识图谱点及其掌握程度。
    *   `data`: `{ "nodes": [ { "id": "函数", "mastery": 80 }, ... ] }`

### 获取学习任务
*   **Endpoint:** `GET /student/study-tasks`
*   **Tags:** `Student`
*   **Response:**
    *   `200 OK`: 待完成的复习或学习任务。
    *   `data`: `{ "tasks": [ { "id": "1", "title": "...", "type": "weakness_review", "priority": "high" } ] }`

### 获取成长趋势
*   **Endpoint:** `GET /student/growth-trend`
*   **Tags:** `Student`
*   **Query Parameters:**
    *   `subject` (optional, string): 学科筛选 (如: 英语)
*   **Response:**
    *   `200 OK`: 过去考试得分和能力的趋势数据。
    *   `data`: `{ "history": [ { "date": "2024-03", "score": 85 }, ... ] }`

### 获取所属班级及教师信息
*   **Endpoint:** `GET /student/classes`
*   **Tags:** `Student`
*   **Response:**
    *   `200 OK`: 学生加入的班级列表及任课教师。
    *   `data`: `{ "classes": [ { "class_id": 1, "name": "高三一班", "subject": "数学", "teacher_name": "张老师", "grade_name": "高三" } ] }`

