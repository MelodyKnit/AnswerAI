# API 文档入口

原有单文件 API 文档已拆分到 `docs/api/` 目录，避免一个文件同时承担约定、对象说明、学生端、教师端和实时接口说明而持续失真。

建议按以下顺序阅读：

1. [docs/api/index.md](docs/api/index.md)：统一约定、通用响应、核心对象。
2. [docs/api/auth-meta.md](docs/api/auth-meta.md)：认证、个人资料、元数据。
3. [docs/api/student.md](docs/api/student.md)：学生端考试、结果、成长画像、学习任务。
4. [docs/api/teacher-classes-questions.md](docs/api/teacher-classes-questions.md)：教师端班级与题库。
5. [docs/api/teacher-exams-review.md](docs/api/teacher-exams-review.md)：教师端组卷、考试、阅卷与重考审批。
6. [docs/api/support.md](docs/api/support.md)：AI 任务、报告、上传、WebSocket。

说明：

- 本组文档以当前 FastAPI 实现为准，按 `backend/app/api/routes/` 与 `backend/app/schemas/` 中的实际接口、请求体和主要响应字段整理。
- 示例 JSON 主要展示 `data` 内业务负载；完整响应仍统一包裹在 `code`、`message`、`data`、`request_id`、`timestamp` 结构中。
- 若后续新增接口，请优先在对应模块文件补充，避免重新回到“大而全单文件”的维护方式。
