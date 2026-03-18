# 腾讯大数据平台查询指南

> 本技能基于 iWiki 文档 [CodeBuddy/ OpenClaw 使用指南](https://iwiki.woa.com/p/4018547797) 构建

---

## 能力描述

你能够调用腾讯大数据平台 API 查询以下信息：

---

## 1. 离线任务失败原因分析

### 平台
- **US 平台**: https://us.woa.com

### 查询方式
需要提供：
- 任务 ID (taskId)
- 实例时间

### 提问示例
> "US任务跑失败了，帮忙看下是什么原因，任务ID: XXXXXXXXXX，实例时间: 2026-02-03"

---

## 2. YARN Application 失败分析

### 平台
- YARN ResourceManager

### 查询方式
需要提供：
- Application ID (application_xxxxx_xxxxx)

### 提问示例
> "帮我分析 application_1740xxx_1234 失败的原因"

---

## 3. 实时任务异常分析

### 平台
- **Oceanus**: https://oceanus.woa.com

### 查询方式
需要提供：
- 任务 ID
- 实例时间

### 提问示例
> "分析 https://oceanus.wa.com/#/task/streaming/detail/XXXXX/XXXXX/ops 的异常信息"

---

## 4. HDFS 文件健康诊断

### 常见错误
```
Caused by: org.apache.hadoop.hdfs.BlockMissingException: 
Could not obtain block: xxx file=xxx
```

### 提问示例
> "任务报错 BlockMissingException，file=/user/hive/warehouse/xxx.db/xxx，帮我看下 hdfs 自动恢复没"

---

## 5. SuperSql 作业分析

### 平台
- **SuperSql**: https://ss-qe-log.woa.com

### 查询方式
需要提供：
- Session ID

### 提问示例
> "https://ss-qe-log.wa.com/v1/session/d85b28c5-11c1-4ff7-9f78-4186036992f4 帮我分析下这个 session"

---

## 6. TDBank 业务信息查询

### 平台
- **TDBank**

### 查询方式
需要提供：
- 表名 (bid)

### 提问示例
> "帮忙查下 b_teg_tube_index 的分区数？"
> "查一下 b_xxx_xxx 表的字段信息"

---

## 7. StarRocks 集群负载分析

### 平台
- **StarRocks (SR)**

### 查询方式
需要提供：
- 集群名称

### 提问示例
> "帮忙看看 starrocks-gz0-teg-common-txt-v33 集群最近的负载？"

---

## 8. SuperSql SQL 执行

> ⚠️ 网络限制：idc 机器和本地可通，devcloud 受限

### 查询方式
需要提供：
- SQL 语句

### 提问示例
> "帮忙执行 supersql 语句：select xxx from db.table where imp_date = '20250314'"

---

## 输出格式

根据查询类型，返回对应的分析结果：
- 任务状态（成功/失败/运行中）
- 错误原因分析
- 建议的解决方案

## 注意事项

1. 部分功能需要配置 CMK
2. 首次使用可能需要较长时间下载模块
3. 内网数据禁止使用境外模型推理
