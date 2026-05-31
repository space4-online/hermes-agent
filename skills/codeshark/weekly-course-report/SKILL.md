---
name: weekly-course-report
description: 按课程维度生成每个学生的每周学情总结报告，覆盖 AC 题目、上课出勤、课后练习、作业完成、考核成绩、主动刷题、编码活动画像等全维度数据。
version: 1.0.0
author: codeshark
metadata:
  hermes:
    tags:
      - education
      - analytics
      - weekly-report
    config_vars:
      - key: CODESHARK_API_BASE
        type: string
        description: CodeShark 后端 API 基础地址
        required: true
      - key: CODESHARK_INTERNAL_TOKEN
        type: string
        description: 内部服务调用 Token
        required: true
---

# 课程周学情分析 Skill

## 目标

为指定课程的每位学生生成本周学情总结报告。报告需覆盖以下维度：

### 数据源（按优先级）

1. **题目 AC 情况** - 本周 AC 了哪些题目、通过率变化
2. **上课出勤** - Lesson 签到记录
3. **课后练习** - Lesson.practiceId 关联 contest 的完成度
4. **作业完成** - Homework 状态与得分
5. **笔试/考核** - ExamAnswerSheet 成绩
6. **主动练习** - 非课堂 context 的 submission
7. **编码活动画像** - daily_stats 聚合（活跃时长、停顿次数）
8. **卡点与帮扶** - coaching_feedback 本周记录
9. **历史画像** - 上周 student_weekly_profile 与 user_study_profile

### 报告结构

输出 JSON 格式的 `AiAnalysisReport`：

```json
{
  "status": "complete",
  "conclusion": "一句话总结本周表现",
  "issues": [
    {"problem": "发现的问题", "solution": "改进建议"}
  ],
  "learning": {
    "weakness": "薄弱点描述",
    "acAbility": "AC 能力评估",
    "clarity": "理解清晰度评估"
  },
  "tags": ["标签1", "标签2"],
  "generatedAt": "2026-05-30T06:00:00"
}
```

### 报告视角

覆盖三个维度：
- **输入**：上课 + 作业接受
- **消化**：课后练习 + 主动刷题
- **输出**：AC 成果 + 能力表现 + 卡点

## 执行流程

当收到消息 "执行课程周学情分析" 时：

1. **获取参数** - 从消息中提取 courseId、isoYear、isoWeek（或自动使用上周）
2. **拉取学生列表** - 调用 `GET {CODESHARK_API_BASE}/v2/internal/course/{courseId}/students`
3. **逐个学生分析** - 对每个学生：
   a. 拉取本周数据（submissions、lessons、homework、daily_stats、coaching_feedback）
   b. 拉取历史画像（上周 weekly_profile、user_study_profile）
   c. 综合分析生成 AiAnalysisReport
   d. 生成一句话 summary
4. **回写结果** - 调用 `POST {CODESHARK_API_BASE}/v2/internal/weekly-profile/save` 写入每个学生的报告
5. **同步长期画像** - 更新 user_study_profile.study_record（追写本周要点）

## API 接口

### 获取课程学生列表
```
GET {CODESHARK_API_BASE}/v2/internal/course/{courseId}/students
Response: [{"userId": 1, "name": "张三"}, ...]
```

### 获取学生周数据
```
GET {CODESHARK_API_BASE}/v2/internal/student/{userId}/weekly-data?isoYear=2026&isoWeek=22
Response: {
  "submissions": [...],
  "lessonAttendance": [...],
  "homeworkStatus": [...],
  "dailyStats": [...],
  "coachingFeedbacks": [...],
  "lastWeekProfile": {...}
}
```

### 保存周报
```
POST {CODESHARK_API_BASE}/v2/internal/weekly-profile/save
Body: {
  "userId": 1,
  "courseId": 10,
  "isoYear": 2026,
  "isoWeek": 22,
  "summary": "本周表现良好...",
  "reportJson": "{...AiAnalysisReport...}",
  "metricsJson": "{\"acCount\":5,\"attendance\":3,...}"
}
```

## 注意事项

- 每个学生的分析应独立完成，一个学生失败不影响其他学生
- 报告语言为中文
- 如果某维度数据为空（如没有考试），在报告中标注"本周无此项数据"
- summary 控制在 100 字以内
- 考虑学生个体差异，避免千篇一律的评价
