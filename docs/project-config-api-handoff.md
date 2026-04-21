# 项目级天气与短信配置 API 交接表

> 更新时间：2026-04-21（Asia/Shanghai）
> 相关实现：`src/app/api/http.py`、`src/app/modules/integration/persistence.py`、`src/app/services/scheduler_service.py`

## 1. 交付目标

本次交付新增了项目级配置能力，解决三个问题：

- 不同旅游项目使用不同的极端天气阈值
- 不同项目使用不同的短信签名和模板码
- 调度器在早 / 中 / 晚发送时，优先读取项目配置和项目模板

## 2. 新增 MySQL 表

表名：`t_project_notification_config`

核心字段：

- `tenant_id`
- `project_id`
- `project_name`
- `weather_enabled`
- `qweather_credential_id`
- `qweather_location_id`
- `qweather_lat`
- `qweather_lon`
- `weather_alert_threshold_json`
- `sms_provider`
- `sms_sign_name`
- `sms_template_code_normal`
- `sms_template_code_weather_alert`
- `manual_takeover_target`

用途：

- 项目默认天气位置和阈值
- 项目默认短信签名
- 项目默认常规 / 天气预警模板码
- 异常转人工时的责任落点

## 3. 新增 API

### 3.1 查询全部项目配置

`GET /api/project-configs`

权限：

- `admin`

返回重点：

- `data.total`
- `data.items[]`

### 3.2 查询单个项目配置

`GET /api/project-configs/{project_id}`

权限：

- `admin`

### 3.3 新增或更新项目配置

`PUT /api/project-configs/{project_id}`

权限：

- `admin`

请求体示例：

```json
{
  "project_name": "新疆阿勒泰团",
  "weather_enabled": true,
  "qweather_credential_id": "QW-CRED-001",
  "qweather_location_id": "101130101",
  "qweather_lat": "43.82",
  "qweather_lon": "87.62",
  "weather_alert_thresholds": {
    "warning_levels": ["yellow", "orange", "red"],
    "min_temp_c": 2
  },
  "sms_provider": "aliyun",
  "sms_sign_name": "新疆团",
  "sms_template_code_normal": "SMS_XJ_NORMAL",
  "sms_template_code_weather_alert": "SMS_XJ_ALERT",
  "manual_takeover_target": "管家值班群"
}
```

## 4. 调度器使用方式

调度器执行顺序：

1. 按早 / 中 / 晚 cron 扫描行程
2. 读取项目配置
3. 合并项目默认天气坐标
4. 获取天气
5. 按项目阈值判断是否触发 `weather_alert`
6. 优先选择项目模板
7. 若模板未设置短信签名 / 模板码，则回退到项目默认配置

当前短信模板码回退顺序：

1. 模板 `provider_template_code`
2. 项目配置 `sms_template_code_weather_alert` 或 `sms_template_code_normal`

当前短信签名回退顺序：

1. 模板 `sms_sign_name`
2. 项目配置 `sms_sign_name`

## 5. 本地运行密钥落点

真实和风天气密钥没有写入公开文档和 SQL seed。

本地运行配置落点：

- `.env.local`

当前已写入：

- `QWEATHER_CREDENTIAL_ID`
- `QWEATHER_API_KEY`

仍需补齐：

- `QWEATHER_API_HOST`

说明：

- 和风天气要求使用控制台分配的独立 `API Host`
- 在拿到正式 Host 之前，系统会继续走 mock provider，避免因为占位值导致启动失败

## 6. 交付注意事项

- 客户交付包不要直接带 `.env.local`
- 生产环境建议改为部署平台密钥管理或容器环境变量
- 如果客户要求后台可维护密钥，再单独做“密钥加密存储 + 授权查看”能力，不建议现在直接通过业务 API 回传真实 API Key
