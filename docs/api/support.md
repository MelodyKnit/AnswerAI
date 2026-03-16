# 支撑能力 API

本页覆盖 AI 任务状态、报告中心、文件上传与 WebSocket 实时通道。

## 1. AI 任务状态

### GET /ai/tasks/status

查询单个 AI 任务的状态。

查询参数：

| 参数 | 类型 | 必填 |
| --- | --- | --- |
| task_id | string | 是 |

返回：

```json
{
  "task": {
    "task_id": "task_xxx",
    "type": "report_generate",
    "status": "completed",
    "progress": 100,
    "resource_type": "report",
    "resource_id": 501
  }
}
```

### POST /ai/tasks/status/batch

批量查询 AI 任务状态。

请求体：

```json
{
  "task_ids": ["task_a", "task_b"]
}
```

返回：

```json
{
  "tasks": []
}
```

## 2. 报告中心

### GET /reports

返回当前用户可见的报告列表。教师看到自己创建的报告，学生看到与自己关联的报告。

查询参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| report_type | string | 可选，按类型过滤 |
| page | integer | 页码 |
| page_size | integer | 每页数量 |

说明：

- 当前实现返回的 `total` 为本页 items 长度，而非全量总数。

### GET /reports/detail

查看单份报告详情。

查询参数：`report_id`。

返回：

- `report`: 报告摘要对象。
- `sections`: 报告内容分节数组，取自 `content_json.sections`。

### POST /reports/generate

生成报告，同时创建一条 AI 任务。

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| report_type | string | 是 | `exam`、`class`、`student`、`knowledge_topic` |
| exam_id | integer | 否 | 考试维度报告时使用 |
| class_id | integer | 否 | 班级维度报告时使用 |
| student_id | integer | 否 | 指定学生时使用；学生本人请求时可不传 |
| title | string | 否 | 自定义标题 |

返回：

```json
{
  "task_id": "task_report_xxx",
  "status": "completed",
  "report": {
    "id": 501,
    "report_type": "exam",
    "title": "高一数学周测报告",
    "status": "ready"
  }
}
```

### POST /reports/export

为已有报告生成导出地址。

请求体：

```json
{
  "report_id": 501
}
```

返回中 `report.file_url` 会被更新为类似 `/exports/reports/501.json` 的路径。

### POST /reports/share

返回一条可分享链接。

请求体：

```json
{
  "report_id": 501
}
```

返回：

```json
{
  "report_id": 501,
  "share_url": "https://example.local/reports/share/501"
}
```

## 3. 文件上传

### POST /upload/image

教师上传图片，用于题目插图等场景。

### 认证

仅教师可调用。

### 请求方式

- `multipart/form-data`
- 表单字段名：`file`

### 限制

- 支持 MIME 类型：`image/jpeg`、`image/png`、`image/webp`、`image/gif`
- 文件不能为空
- 文件大小不能超过 8 MB

### 成功返回

```json
{
  "file_name": "8a7c....png",
  "content_type": "image/png",
  "size": 102400,
  "url": "/uploads/8a7c....png"
}
```

## 4. WebSocket 实时通道

## 4.1 WS /ws/exams/{exam_id}/submissions/{submission_id}

### 考试提交通道用途

监听单份提交记录的实时事件，主要用于考试过程中的自动保存、交卷和成绩发布通知。

### 考试提交通道首包

```json
{
  "event": "subscribed",
  "data": {
    "channel": "submission:1001:9001"
  }
}
```

### 考试提交通道保活

客户端可发送：

```json
{
  "event": "ping"
}
```

服务端返回：

```json
{
  "event": "pong",
  "data": {
    "channel": "submission:1001:9001"
  }
}
```

### 考试提交通道事件

- `submission_started`
- `answer_saved`
- `behavior_reported`
- `submission_submitted`
- `results_published`

## 4.2 WS /ws/ai-tasks

### AI 任务通道用途

监听一个或多个 AI 任务的进度变化。

### AI 任务通道首包

```json
{
  "event": "connected",
  "data": {
    "message": "send {'task_ids': [...]} to subscribe"
  }
}
```

### AI 任务通道订阅

客户端发送：

```json
{
  "task_ids": ["task_a", "task_b"]
}
```

服务端返回：

```json
{
  "event": "subscribed",
  "data": {
    "task_ids": ["task_a", "task_b"]
  }
}
```

### AI 任务通道心跳

客户端同样可以发送 `{"event": "ping"}`，服务端会返回当前已订阅任务列表对应的 `pong`。
