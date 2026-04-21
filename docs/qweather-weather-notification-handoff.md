# 和风天气接入与定时通知交接表

> 更新时间：2026-04-21（Asia/Shanghai）
> 适用范围：旅游通知系统天气接入、早中晚定时提醒、项目级短信差异化发送
> 相关代码：`src/app/modules/integration/weather_provider.py`、`src/app/services/scheduler_service.py`、`src/app/modules/integration/sms_provider.py`、`src/app/services/template_service.py`

## 1. 目标

本交接表用于说明当前项目如何接入和风天气（QWeather）官方 API，并支撑以下业务目标：

- 按行程目的地获取天气数据
- 每天固定早 / 中 / 晚 触发通知任务
- 根据天气场景决定发送常规提醒或天气预警提醒
- 不同项目使用不同短信模板、签名或发送策略

## 2. 当前代码现状

### 2.1 天气能力

- `src/app/modules/integration/weather_provider.py` 目前仍是 `mock` 实现
- 当前天气结果为随机生成，未接入外部天气服务
- 现有 `WeatherInfo` 字段只有：
  - `destination`
  - `condition`
  - `temperature`
  - `warning_level`

### 2.2 调度能力

- `src/app/services/scheduler_service.py` 当前使用 `APScheduler`
- 目前仅有演示性质的每 1 分钟扫描任务
- 当前规则只覆盖：
  - 出发前 1 天
  - 出发当天
  - 行程结束当天 / 次日
- 还没有“早 / 中 / 晚”时间槽调度

### 2.3 短信能力

- `src/app/modules/integration/sms_provider.py` 已支持：
  - `MockSMSProvider`
  - `AliyunSMSProvider`
- 阿里云短信目前默认只读一个 `ALIYUN_SMS_TEMPLATE_CODE`
- 这意味着当前还不支持“每个项目用不同模板码 / 不同签名 / 不同文案参数”

### 2.4 模板与规则能力

- `src/app/services/template_service.py` 已有通知模板存储与 Jinja2 渲染能力
- `docs/api-contract.md` 已定义 `/api/notifications/rules*`
- 当前规则枚举已支持：
  - `stage`: `pre_trip` / `in_trip` / `post_trip`
  - `time_slot`: `morning` / `afternoon` / `evening` / `night` / `all_day`
  - `scene`: `normal` / `weather_alert` / `delay` / `complaint` / `manual`

结论：
项目已经具备“规则 + 模板 + 调度 + 发送”的骨架，但天气接入和项目级短信配置还没有真正落地。

## 3. 官方文档确认结果

本次仅核对了和风天气官方文档 `https://dev.qweather.com/docs/api/`。

### 3.1 推荐使用的接口

#### 1) 城市搜索 GeoAPI

- 路径：`/geo/v2/city/lookup`
- 用途：把目的地名称转换为 `location id`、经纬度、时区
- 适用场景：
  - 录入新行程时补全天气查询坐标
  - 解决“同名城市”问题

#### 2) 实时天气

- 路径：`/v7/weather/now`
- 用途：获取当前天气、温度、降水、能见度等
- 适用场景：
  - 早 / 中 / 晚常规提醒中的天气摘要
  - 出发前即时天气提示

#### 3) 逐小时天气预报

- 路径：`/v7/weather/{hours}`
- 推荐值：`24h` 或 `72h`
- 用途：获取未来 24-72 小时天气
- 适用场景：
  - 次日出行提醒
  - 午间 / 晚间判断未来是否降雨、降温、大风

#### 4) 每日天气预报

- 路径：`/v7/weather/{days}`
- 推荐值：`3d` 或 `7d`
- 用途：获取未来多天天气趋势
- 适用场景：
  - 行前打包提醒
  - 长线团行程准备建议

#### 5) 分钟级降水

- 路径：`/v7/minutely/5m`
- 限制：文档标注为中国区域未来 2 小时、每 5 分钟降水预报
- 适用场景：
  - 行中临近降雨提醒
  - 景点 / 户外活动前的短时雨提示

#### 6) 实时天气预警

- 路径：`/weatheralert/v1/current/{latitude}/{longitude}`
- 用途：查询官方生效中的极端天气预警
- 适用场景：
  - 暴雨 / 大风 / 雷电 / 寒潮等强提醒
  - 命中后将 `scene` 切换为 `weather_alert`

### 3.2 鉴权方式

官方文档支持两种方式：

- `Authorization: Bearer <jwt>`
- `X-QW-Api-Key: <api-key>`

建议：

- 生产环境优先使用 JWT
- 当前联调阶段可先使用 API Key 直连

注意：

- 官方“身份认证”页写明自 `2027-01-01` 起会限制 API KEY 每日请求量
- 官方“项目和凭据”页写明自 `2027-02-01` 起会逐步限制 API KEY 每日请求量
- 两个页面日期不一致，正式上线前应再次确认官方口径

### 3.3 Host 规则

- 和风天气要求使用开发者自己的独立 `API Host`
- 不建议继续使用公共地址
- 文档说明公共 API 地址将从 2026 年起逐步停止服务

因此本项目不能只保存 `API Key`，还必须保存：

- `API Host`
- 鉴权方式
- 如使用 JWT，还需要 `Project ID`、`Key ID`、私钥

## 4. 建议的系统配置

不要把真实凭据写进仓库，统一通过环境变量注入。

建议新增环境变量：

```env
QWEATHER_AUTH_MODE=api_key
QWEATHER_API_HOST=your-api-host
QWEATHER_API_KEY=your-api-key

# JWT 模式预留
QWEATHER_PROJECT_ID=your-project-id
QWEATHER_KEY_ID=your-key-id
QWEATHER_PRIVATE_KEY_PATH=/secure/path/qweather-ed25519-private.pem

# 调度
NOTIFICATION_TIMEZONE=Asia/Shanghai
NOTIFICATION_MORNING_CRON=0 8 * * *
NOTIFICATION_NOON_CRON=0 12 * * *
NOTIFICATION_EVENING_CRON=0 19 * * *
```

如果一个部署实例要服务多个项目，建议再加：

```env
DEFAULT_WEATHER_PROVIDER=qweather
```

项目级配置不要走环境变量硬编码，应该入库。

## 5. 建议的数据配置模型

为了满足“每个项目发送短信都是不一样的”，建议把短信配置拆成“项目配置 + 规则 + 模板”三层。

### 5.1 项目天气配置

建议新增一张配置表，例如 `project_weather_config`：

| 字段 | 说明 |
| --- | --- |
| `project_id` | 项目 ID |
| `qweather_location_id` | 默认天气城市 ID |
| `qweather_lat` | 纬度 |
| `qweather_lon` | 经度 |
| `timezone` | 项目时区 |
| `weather_enabled` | 是否启用天气能力 |
| `weather_alert_threshold` | 天气告警阈值 JSON |

### 5.2 项目短信通道配置

建议新增一张配置表，例如 `project_channel_config`：

| 字段 | 说明 |
| --- | --- |
| `project_id` | 项目 ID |
| `channel` | `sms` / `wechat_work_group` / `email` |
| `sms_provider` | 如 `aliyun` |
| `sms_sign_name` | 短信签名 |
| `provider_template_code` | 供应商模板码 |
| `fallback_channel` | 失败后的兜底通道 |
| `manual_takeover_group` | 人工接管群或负责人 |

### 5.3 项目通知模板

现有 `NotificationTemplate` 可继续用，但建议补充以下维度：

| 字段 | 说明 |
| --- | --- |
| `tenant_id` | 租户 |
| `project_id` | 项目 |
| `stage` | `pre_trip` / `in_trip` / `post_trip` |
| `time_slot` | `morning` / `afternoon` / `evening` |
| `scene` | `normal` / `weather_alert` |
| `channel` | `sms` 等 |
| `content` | Jinja 模板 |
| `provider_template_code` | 外部短信模板码 |

## 6. 早中晚定时发送建议

### 6.1 时间槽定义

建议先统一为：

- 早：`08:00`
- 中：`12:00`
- 晚：`19:00`

如果项目有差异，再允许项目级覆盖。

### 6.2 调度逻辑

建议将当前单个扫描任务改为三个 cron 任务：

1. `morning_dispatch_job`
2. `noon_dispatch_job`
3. `evening_dispatch_job`

每个任务统一执行以下链路：

1. 根据当前时间槽查启用中的项目
2. 找出当前需要发送的行程
3. 获取目的地 `location_id` / 经纬度
4. 调用和风天气接口
5. 计算 `scene`
6. 读取项目级模板和短信通道配置
7. 渲染短信内容
8. 发送短信
9. 失败则走 fallback 或人工接管
10. 写审计日志

### 6.3 场景判定建议

建议最少支持以下规则：

| 条件 | scene | 说明 |
| --- | --- | --- |
| 无预警且未来 12 小时天气平稳 | `normal` | 常规提醒 |
| 存在官方天气预警 | `weather_alert` | 强提醒 |
| 分钟级降水 2 小时内有雨 | `weather_alert` | 行中短时雨提醒 |
| 逐小时预报显示明显降温 / 大风 / 暴雪 | `weather_alert` | 提前准备 |

## 7. 短信内容按项目差异化的实现建议

不要把“每个项目的短信内容”写死在 `scheduler_service.py` 里。

建议采用以下优先级：

1. `project_id + stage + time_slot + scene + channel` 精准匹配
2. `project_id + stage + time_slot + channel` 默认匹配
3. `tenant_id + stage + time_slot + scene + channel` 租户级默认
4. 系统默认模板

模板变量建议统一：

```json
{
  "project_name": "新疆阿勒泰团",
  "customer_name": "张三",
  "destination": "乌鲁木齐",
  "departure_date": "2026-04-22",
  "weather_text": "乌鲁木齐今日小雨，12-18℃",
  "alert_title": "大风蓝色预警",
  "packing_tip": "建议携带雨具和薄外套",
  "concierge_name": "小王管家",
  "contact_phone": "13800000000"
}
```

## 8. 建议的接口落地方式

### 8.1 行程创建 / 更新时

- 输入：目的地名称
- 动作：
  - 调用 `/geo/v2/city/lookup`
  - 保存 `location_id`、经纬度、时区
- 好处：
  - 调度时不用重复做城市模糊搜索
  - 降低天气查询失败率

### 8.2 定时任务执行时

- 常规提醒：
  - 调 `weather/now`
  - 调 `weather/24h` 或 `weather/72h`
- 预警提醒：
  - 调 `weatheralert`
- 国内行中短时雨：
  - 追加调 `minutely/5m`

### 8.3 API 调用优先级建议

- 行前：`daily + hourly`
- 行中：`now + alert + minutely(国内可用时)`
- 行后：通常不需要天气接口

## 9. 当前代码改造建议

### P0

- 将 `WeatherProvider` 从 mock 改为可配置 Provider
- 新增 `QWeatherProvider`
- 在调度器中引入 `morning/noon/evening` 三个 cron 任务
- 模板选择增加 `project_id/time_slot/scene`
- 短信发送增加项目级 `sign_name/template_code`

### P1

- 新增城市信息持久化
- 新增天气缓存和失效策略
- 新增天气预警转人工接管逻辑
- 为不同项目配置不同发送窗口和兜底通道

### P2

- 支持 JWT 鉴权
- 支持分钟级降水仅中国线路启用
- 支持天气接口限流、重试和熔断
- 支持运营后台维护项目模板和天气阈值

## 10. 风险与注意事项

### 10.1 凭据安全

- 不要在代码、测试、文档中保存真实 API Key
- 凭据必须放环境变量或密钥管理服务
- 建议在和风天气控制台配置：
  - API 限制
  - IP 白名单或应用限制

### 10.2 缓存

官方文档明确提醒：

- 实时天气不能缓存过久
- GeoAPI 不能做违规批量缓存
- 应考虑跨时区、跨天、夏令时影响

本项目建议：

- `city lookup` 结果长期缓存到业务库
- `weather now` 缓存 10-20 分钟
- `hourly/daily` 缓存 30-60 分钟
- `alert` 不建议长缓存

### 10.3 业务边界

- 不是所有天气变化都要发短信
- 应先按项目定义阈值，避免骚扰用户
- 强提醒只在预警、暴雨、大风、降雪、明显降温等场景触发

## 11. 推荐实施顺序

1. 先把目的地映射到 `location_id + lat + lon`
2. 再实现 `QWeatherProvider`
3. 再把调度器改成早 / 中 / 晚三段
4. 再补项目级短信配置和模板映射
5. 最后补告警阈值、缓存、人工接管

## 12. 官方文档链接

- 开发文档入口：<https://dev.qweather.com/docs/api/>
- 项目和凭据：<https://dev.qweather.com/docs/configuration/project-and-key/>
- 身份认证：<https://dev.qweather.com/docs/configuration/authentication/>
- API Host：<https://dev.qweather.com/docs/configuration/api-host/>
- 城市搜索 GeoAPI：<https://dev.qweather.com/docs/api/geoapi/city-lookup/>
- 实时天气：<https://dev.qweather.com/docs/api/weather/weather-now/>
- 每日天气预报：<https://dev.qweather.com/docs/api/weather/weather-daily-forecast/>
- 逐小时天气预报：<https://dev.qweather.com/docs/api/weather/weather-hourly-forecast/>
- 分钟级降水：<https://dev.qweather.com/docs/api/minutely/minutely-precipitation/>
- 实时天气预警：<https://dev.qweather.com/docs/api/warning/weather-alert/>
- 缓存最佳实践：<https://dev.qweather.com/docs/best-practices/cache/>
- 安全指南：<https://dev.qweather.com/docs/best-practices/security-guidelines/>
