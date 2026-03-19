# 认证与元数据 API

本页覆盖 `auth.py` 与 `meta.py` 中当前实现的接口，适合作为登录、注册、全局枚举与知识点树的对接依据。

## 1. POST /auth/register

### 注册用途

创建学生或教师账号。注册成功后直接返回访问令牌，前端无需再立即调用一次登录接口。

### 注册认证

无需认证。

### 注册请求体

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| role | string | 是 | 仅允许 `student` 或 `teacher` |
| name | string | 是 | 姓名 |
| username | string | 是 | 3 到 32 位，只允许字母和数字，且必须包含字母 |
| email | string | 是 | 邮箱，需唯一 |
| password | string | 是 | 至少 8 位 |
| confirm_password | string | 是 | 必须与 `password` 一致 |
| phone | string | 否 | 手机号 |
| school_name | string | 否 | 学校名称 |
| grade_name | string | 否 | 年级名称 |
| teacher_invite_code | string | 否 | 预留字段，当前路由未使用 |
| class_code | string | 否 | 学生注册时可直接加入班级的邀请码 |

### 注册处理流程

1. 检查邮箱是否已注册。
2. 检查用户名是否已存在。
3. 创建用户并写入加密后的密码。
4. 若角色为学生且传入 `class_code`，尝试通过班级邀请码建立 `ClassStudent` 关系。
5. 生成 JWT 访问令牌并返回。

### 注册成功返回

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "role": "student",
    "name": "张三",
    "username": "zhangsan01",
    "email": "student@example.com"
  }
}
```

### 注册常见失败

- `409`: 邮箱已注册。
- `409`: 用户名已注册。
- `422`: 用户名格式或密码确认不合法。

## 2. POST /auth/login

### 登录用途

使用邮箱或用户名登录。

### 登录请求体

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| login_id | string | 是 | 邮箱或用户名 |
| password | string | 是 | 明文密码 |

### 登录返回重点

- `access_token`: JWT。
- `token_type`: 固定为 `bearer`。
- `expires_in`: 当前返回 `86400` 分钟级时长换算值。
- `user`: 精简用户信息。

### 登录成功返回

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 21,
    "role": "teacher",
    "name": "李老师",
    "username": "lilaoshi",
    "email": "teacher@example.com"
  }
}
```

### 登录常见失败

- `401`: 账号不存在，或邮箱/用户名与密码不匹配。

## 3. GET /auth/me

### 当前用户用途

返回当前登录用户完整资料，用于页面刷新后恢复用户状态。

### 当前用户认证

需要登录。

### 当前用户返回字段

```json
{
  "user": {
    "id": 21,
    "role": "teacher",
    "name": "李老师",
    "username": "lilaoshi",
    "email": "teacher@example.com",
    "phone": "13800000000",
    "avatar_url": "/uploads/avatar.png",
    "school_name": "第一中学",
    "grade_name": "高一",
    "status": "active",
    "created_at": "2026-03-16T10:00:00+00:00"
  }
}
```

## 4. POST /users/profile/update

### 更新资料用途

更新当前用户资料。

### 更新资料请求体

所有字段均为可选，仅会更新传入字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| name | string | 姓名 |
| phone | string | 手机号 |
| avatar_url | string | 头像地址 |
| school_name | string | 学校名称 |
| grade_name | string | 年级名称 |

### 更新资料返回

返回更新后的完整 `user` 对象，结构与 `/auth/me` 相同。

## 5. POST /users/password/change

### 修改密码用途

修改当前用户密码。

### 修改密码请求体

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| old_password | string | 是 | 原密码 |
| new_password | string | 是 | 新密码，至少 8 位 |

### 修改密码成功返回

```json
{
  "success": true
}
```

### 修改密码常见失败

- `400`: 原密码错误。

## 6. POST /users/feedback/create

### 提交用户反馈用途

创建一条用户反馈记录，支持文本问题描述与图片证据，后端落库到 AI 任务表中（`type=user_feedback`）。

### 反馈请求体

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| category | string | 是 | 仅允许 `bug`、`product`、`design`、`other` |
| content | string | 是 | 反馈正文 |
| images | array | 否 | 图片 URL 列表，最多 6 条 |
| page_path | string | 否 | 问题发生页面路径 |

### 反馈校验规则

- 空图片地址会被自动忽略。
- 单条图片地址长度不能超过 500。
- 图片数量超过 6 会返回 `400`。

### 反馈成功返回

```json
{
  "feedback_id": 123,
  "status": "submitted"
}
```

## 7. GET /meta/subjects

### 学科列表用途

返回系统中状态为 `active` 的学科列表，通常用于登录后筛选器、组卷表单和题库表单。

### 学科列表返回

```json
{
  "items": [
    {"id": 1, "code": "math", "name": "数学"},
    {"id": 2, "code": "physics", "name": "物理"}
  ]
}
```

## 8. GET /meta/grades

### 年级枚举用途

返回内置年级枚举。该接口不查数据库，直接返回服务端常量。

### 年级枚举返回

```json
{
  "items": [
    {"code": "grade7", "name": "初一"},
    {"code": "grade10", "name": "高一"}
  ]
}
```

## 9. GET /meta/question-types

### 题型枚举用途

返回系统当前支持的题型枚举，供题库、考试试卷、答题页和统计图统一展示。

### 当前题型枚举

| code | name |
| --- | --- |
| single_choice | 单选题 |
| multiple_choice | 多选题 |
| judge | 判断题 |
| blank | 填空题 |
| essay | 简答题 |
| material | 材料题 |

## 10. GET /meta/knowledge-points/tree

### 知识点树用途

按学科返回兼容树节点结构。当前系统已移除独立 knowledge_points 表，接口会返回一层 subject 节点，用于前端兼容展示。

### 知识点树查询参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 是 | 学科中文名，例如 `数学` |

### 知识点树返回特点

- 若学科不存在，返回空数组而非错误。
- 节点包含 `children` 字段，前端可直接递归渲染。
- 当前默认只返回一层节点：`name/path` 均为 subject 名称。

### 知识点树返回示例

```json
{
  "items": [
    {
      "id": 10,
      "name": "数学",
      "path": "数学",
      "level": 1,
      "children": []
    }
  ]
}
```
