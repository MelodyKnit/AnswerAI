# 前端页面及路由文档

此文档主要针对系统中所有前端页面（页面级组件）及其路由进行梳理，便于前后端对接和理解系统界面结构。

## 1. 公共访问及基础部分（营销与系统）

| 路由路径 | 页面名 (Name) | 视图文件 (.vue) | 描述 / 主要功能 | 是否需要登录 |
| --- | --- | --- | --- | --- |
| / | home | HomeView | **落地/营销页**：介绍平台特点。 | 否 |
| /app/auth | uth | AuthView | **登录/注册页**：双角色统一入口，支持邮箱/用户名登录。 | 否 |
| /app/system/foundation | design-foundation | DesignSystemView | **组件库/规范展示**：系统基础视觉语言与布局骨架组件库。 | 否 |
| /:pathMatch(.*)* | 
ot-found | NotFoundView | **404错误页**：未匹配到路由时展示的毛玻璃高颜值错误引导页。 | 否 |

---

## 2. 学生端 (Student)

所有学生端业务页面通常要求在登录后访问且含有学生权限。

| 路由路径 | 页面名 (Name) | 视图文件 (.vue) | 描述 / 主要功能 |
| --- | --- | --- | --- |
| /app/student/dashboard | student-dashboard | StudentDashboardView | **学生控制台主面板**：聚合近期考试、错题概览、学习计划及薄弱点提示。 |
| /app/student/exams | student-exams | StudentExamsView | **考试列表**：待考及历史考试的管理列表。 |
| /app/student/exams/:id/prep | student-exam-prep | StudentExamPrepView | **考试前准备**：考前说明展示及设备防作弊自检。 |
| /app/student/exams/:id/session/:sessionId | student-exam-session | StudentExamSessionView | **考试进行中**：实时答题界面（利用 WebSocket 实时同步及保存防丢失）。 |
| /app/student/results/:id | student-results-overview | StudentResultsOverviewView | **单次考试成绩报告**：考试成绩分析、错题一览、风险与提升点总结。 |
| /app/student/results/:id/question/:questionId | student-results-question | StudentQuestionDetailView | **考试错题详解**：单题判卷细节和扣分项拆解。 |
| /app/student/ai-chat | student-ai-chat | StudentAiChatView | **AI 辅导答疑**：针对特定错题发起上下文提问和解析对话（基于流式 WebSocket 推送）。 |
| /app/student/analytics/knowledge-map | student-knowledge-map | StudentKnowledgeMapView | **知识图谱/弱点雷达**：基于做题历史分析得出的知识点掌握度。 |
| /app/student/study-plan | student-study-plan | StudentStudyPlanView | **个性化学习计划**：基于错题与弱项的 AI 补缺任务规划。 |
| /app/student/growth | student-growth | StudentGrowthView | **个人成长档案**：分数长线趋势及学习轨迹追踪。 |

---

## 3. 教师端 (Teacher)

所有教师端功能页面要求登录验证，并具备教师角色。部分界面设计采用了极简、移动端优先体验。

| 路由路径 | 页面名 (Name) | 视图文件 (.vue) | 描述 / 主要功能 |
| --- | --- | --- | --- |
| /app/teacher/dashboard | 	eacher-dashboard | TeacherDashboardView | **教师综合工作台**：班级、考试核心数据总览，快速发起任务。 |
| /app/teacher/classes | 	eacher-classes | TeacherClassesView | **班级列表管理**：自己所带班级的清单。 |
| /app/teacher/classes/create | 	eacher-class-create | TeacherClassCreateView | **创建新班级**：表单录入并生成班级分享邀请码。 |
| /app/teacher/classes/:id | 	eacher-class-detail | TeacherClassDetailView | **班级工作区/详情**：管理班级成员（支持删除学生）、查看邀请码（点击复制）。 |
| /app/teacher/exams | 	eacher-exams | TeacherExamsView | **考试管理**：已发布、批改中或已结束的各项测试概览。 |
| /app/teacher/exams/create | 	eacher-exam-create | TeacherExamCreateView | **发布/组卷**：从题库抽设并安排新的考试给对应班级。 |
| /app/teacher/exams/:id | 	eacher-exam-detail | TeacherExamDetailView | **考试详情页**：考场监管信息，提交情况以及得分概览统计。 |
| /app/teacher/questions | 	eacher-questions | TeacherQuestionsView | **题库资产管理**：维护客观题与主观题，包含富文本和图片资源上传。 |
| /app/teacher/review | 	eacher-review | TeacherReviewView | **阅卷/批改任务**：处理学生主观题的（人工或AI辅助）线上批阅过程。 |
| /app/teacher/settings | 	eacher-settings | TeacherSettingsView | **教师设置汇总入口**。 |
| /app/teacher/settings/profile | 	eacher-settings-profile | TeacherSettingsProfileView | **个人资料设置**：修改教师自己的信息。 |
| /app/teacher/settings/notifications | 	eacher-settings-notifications | TeacherSettingsNotificationsView | **消息通知设置**：各项事件提醒开关。 |
| /app/teacher/settings/security | 	eacher-settings-security | TeacherSettingsSecurityView | **账户安全**：管理密码与绑定账号。 |

---

## 4. 路由与权限架构

整个应用挂载在 #app 下，Vue Router 主要守卫在 outer.beforeEach 中。
- **白名单校验**：['home', 'auth', 'not-found', 'design-foundation'] 允许未登录访问。
- **持久化及重刷**：页面刷新阶段如未加载本地缓存的 Token 及 User 实体，会静默请求并解析 uthStore.fetchUser()。
- **应用骨架壳 (AppShell)**：除公共宣传页以外，全部受保护业务级视图将内嵌渲染在 AppShell.vue 内（支持动态显隐底部导航等）。