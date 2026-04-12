-- MySQL 8.0+
-- 适用范围：行程管理 + 通知中心（模板/规则/发送记录）
-- 字符集：utf8mb4

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS t_notification_attempt;
DROP TABLE IF EXISTS t_notification_task;
DROP TABLE IF EXISTS t_notification_rule_channel;
DROP TABLE IF EXISTS t_notification_rule;
DROP TABLE IF EXISTS t_notification_template;
DROP TABLE IF EXISTS t_lifecycle_playbook;
DROP TABLE IF EXISTS t_trip;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE t_trip (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    trip_code           VARCHAR(64) NOT NULL COMMENT '行程编号（业务唯一）',
    destination         VARCHAR(128) NOT NULL COMMENT '目的地',
    team_id             VARCHAR(64) NOT NULL COMMENT '团号',
    start_date          DATE NOT NULL COMMENT '开始日期',
    end_date            DATE NOT NULL COMMENT '结束日期',
    participants        INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '参团人数',
    status              ENUM('planned','in_progress','completed','cancelled') NOT NULL DEFAULT 'planned' COMMENT '行程状态',
    owner_user_id       VARCHAR(64) NOT NULL DEFAULT 'admin' COMMENT '归属用户',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_trip_code (trip_code),
    KEY idx_team_id (team_id),
    KEY idx_status_dates (status, start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='行程主表';

CREATE TABLE t_lifecycle_playbook (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    stage               ENUM('pre_trip','in_trip','post_trip') NOT NULL COMMENT '阶段：行前/行中/行后',
    time_node           VARCHAR(64) NOT NULL COMMENT '时间节点',
    core_work           VARCHAR(128) NOT NULL COMMENT '核心工作',
    action_detail       TEXT NOT NULL COMMENT '具体执行动作',
    sort_order          INT UNSIGNED NOT NULL DEFAULT 100 COMMENT '排序值',
    is_active           TINYINT(1) NOT NULL DEFAULT 1,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_stage_sort (stage, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='行程执行流程表（来源于你提供的表格）';

CREATE TABLE t_notification_template (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    template_code       VARCHAR(64) NOT NULL COMMENT '模板编码（业务唯一）',
    template_name       VARCHAR(128) NOT NULL,
    notification_type   ENUM('pre_trip_reminder','daily_reminder','risk_alert','satisfaction','farewell') NOT NULL DEFAULT 'daily_reminder',
    channel             ENUM('sms','wechat_work_group','email') NOT NULL DEFAULT 'sms',
    content             TEXT NOT NULL COMMENT '模板内容，支持变量 {{customer_name}}',
    version             INT UNSIGNED NOT NULL DEFAULT 1,
    is_active           TINYINT(1) NOT NULL DEFAULT 1,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_template_code_version (template_code, version),
    KEY idx_template_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='通知模板表';

CREATE TABLE t_notification_rule (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    rule_code           VARCHAR(64) NOT NULL COMMENT '规则编码（业务唯一）',
    rule_name           VARCHAR(128) NOT NULL,
    stage               ENUM('pre_trip','in_trip','post_trip') NOT NULL,
    time_slot           ENUM('morning','afternoon','evening','night','all_day') NOT NULL DEFAULT 'all_day',
    scene               ENUM('normal','weather_alert','delay','complaint','manual') NOT NULL DEFAULT 'normal',
    template_id         BIGINT UNSIGNED NOT NULL,
    priority            INT UNSIGNED NOT NULL DEFAULT 100,
    enabled             TINYINT(1) NOT NULL DEFAULT 1,
    conditions_json     JSON NULL COMMENT '扩展条件（时间节点、标签等）',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_rule_code (rule_code),
    KEY idx_rule_match (stage, time_slot, scene, enabled, priority),
    CONSTRAINT fk_rule_template FOREIGN KEY (template_id) REFERENCES t_notification_template(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='通知规则表';

CREATE TABLE t_notification_rule_channel (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    rule_id             BIGINT UNSIGNED NOT NULL,
    channel             ENUM('sms','wechat_work_group','email') NOT NULL,
    sort_order          TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '渠道顺序：1主渠道，2兜底渠道',
    PRIMARY KEY (id),
    UNIQUE KEY uk_rule_channel (rule_id, channel),
    KEY idx_rule_sort (rule_id, sort_order),
    CONSTRAINT fk_rule_channel_rule FOREIGN KEY (rule_id) REFERENCES t_notification_rule(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='规则渠道表（支持主备兜底）';

CREATE TABLE t_notification_task (
    id                          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    task_code                   VARCHAR(64) NOT NULL COMMENT '任务编号（业务唯一）',
    trip_id                     BIGINT UNSIGNED NOT NULL,
    customer_id                 VARCHAR(64) NOT NULL,
    notification_type           ENUM('pre_trip_reminder','daily_reminder','risk_alert','satisfaction','farewell') NOT NULL,
    primary_channel             ENUM('sms','wechat_work_group','email') NOT NULL DEFAULT 'sms',
    fallback_channel            ENUM('sms','wechat_work_group','email') NULL,
    rendered_content            TEXT NOT NULL,
    idempotency_key             VARCHAR(128) NOT NULL,
    status                      ENUM('pending','sent','failed','manual_intervention','skipped') NOT NULL DEFAULT 'pending',
    retry_count                 TINYINT UNSIGNED NOT NULL DEFAULT 0,
    max_retry                   TINYINT UNSIGNED NOT NULL DEFAULT 2,
    manual_intervention_required TINYINT(1) NOT NULL DEFAULT 0,
    created_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_task_code (task_code),
    UNIQUE KEY uk_idempotency_key (idempotency_key),
    KEY idx_task_trip_status (trip_id, status, created_at),
    CONSTRAINT fk_task_trip FOREIGN KEY (trip_id) REFERENCES t_trip(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='通知任务主表';

CREATE TABLE t_notification_attempt (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    task_id             BIGINT UNSIGNED NOT NULL,
    attempt_no          TINYINT UNSIGNED NOT NULL DEFAULT 1,
    channel             ENUM('sms','wechat_work_group','email') NOT NULL,
    ok                  TINYINT(1) NOT NULL DEFAULT 0,
    reason              VARCHAR(255) NOT NULL DEFAULT '',
    provider_message    VARCHAR(255) NOT NULL DEFAULT '',
    latency_ms          INT UNSIGNED NOT NULL DEFAULT 0,
    attempted_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_task_attempt_no (task_id, attempt_no),
    KEY idx_attempted_at (attempted_at),
    CONSTRAINT fk_attempt_task FOREIGN KEY (task_id) REFERENCES t_notification_task(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='通知发送明细（用于通知中心统计）';

-- ------------------------------
-- Seed 数据（按你提供的流程表 + 页面模板示例）
-- ------------------------------

INSERT INTO t_trip (trip_code, destination, team_id, start_date, end_date, participants, status, owner_user_id)
VALUES
('trip-default-pretrip', '乌鲁木齐-喀纳斯精品线', 'TEAM-DEMO-PRE', '2026-05-08', '2026-05-14', 18, 'planned', 'admin'),
('trip-default-ontrip', '伊犁草原深度游', 'TEAM-DEMO-ON', '2026-04-20', '2026-04-26', 22, 'in_progress', 'admin'),
('trip-default-posttrip', '阿勒泰禾木轻奢团', 'TEAM-DEMO-POST', '2026-03-10', '2026-03-16', 16, 'completed', 'admin');

INSERT INTO t_lifecycle_playbook (stage, time_node, core_work, action_detail, sort_order)
VALUES
('pre_trip', '出发前3天', '游客沟通+行程单处理', '1. 联系游客确认航班信息是否变动；2. 温馨提示游客证件、气候、着装、饮食注意事项；3. 打印行程单并发送给司导，行程单留档保存。', 10),
('pre_trip', '出发前', '资源&物资确认', '1. 确认酒店按要求预定完毕；2. 确定用车（车型、司导配套）是否匹配游客需求；3. 核查无人机、户外桌椅、相关物资筹备情况。', 20),
('pre_trip', '出发前1天', '保险检查+群聊搭建+司导交底', '1. 检查游客保险是否购买完成；2. 监督司导向游客发送短信并主动联系；3. 建立游客服务群并向司导发送行程确认单、行程要求、评分标准、奖励内容；4. 邀请游客进群并发布欢迎语、司导自我介绍；5. 向游客发送乘机前全方位温馨提示。', 30),
('in_trip', '游客落地乌鲁木齐当日', '本地指引+通用提示', '1. 推荐乌鲁木齐游玩景点（国际大巴扎、新疆美术馆、古生态园）及特色美食；2. 发送新疆通用温馨提示（时差、物价、安保、计量单位、饮食、网络等）。', 40),
('in_trip', '每日固定时段', '时段性专属温馨提示', '早上：按春夏秋冬季节发送晨起提示，强调乘车安全、行李放置、安全带佩戴；中午：按季节/雨天发送午间提示，涵盖天气、饮食、防晒防雨、人身财物安全；晚上：发送次日天气、行程简介，提醒退房带好随身物品。', 50),
('in_trip', '特殊游玩场景', '专项安全提示', '骑马：发布自费骑马项目6项核心安全提示；滑雪：提前发布滑雪装备准备、滑雪安全、当地习俗、环境爱护等注意事项；特殊地区（高原、边境口岸、极寒、紫外线强）发布专属提示。', 60),
('in_trip', '全程', '三方协调沟通', '实时协调游客、司导、旅行社三方问题，及时解决并沟通游客行程中遇到的各类问题。', 70),
('post_trip', '下团即时', '欢送+满意度调研', '1. 向游客发送正式欢送词；2. 开展客户满意度调查，并将结果及时反馈给客服、销售岗位。', 80),
('post_trip', '下团后短期内', '售后跟进+客户存档', '1. 做好游客后续跟进及全流程售后服务；2. 对高品质游客信息进行专项存档，同步反馈给销售岗位。', 90),
('post_trip', '售后末期', '群聊解散', '向游客发送群解散通知及祝福，正式解散游客服务群。', 100);

INSERT INTO t_notification_template (template_code, template_name, notification_type, channel, content, version, is_active)
VALUES
('tpl-default-trip-start', '默认行程提醒', 'daily_reminder', 'sms', '{{customer_name}}，您的{{destination}}行程即将开始，请准时集合。', 1, 1),
('tpl-pretrip-flight-notice', '行前3天-航班与行前提示', 'pre_trip_reminder', 'wechat_work_group', '亲爱的游客朋友们：请确认航班和证件信息，提前2-3小时到机场，注意行李规格和安检要求。', 1, 1),
('tpl-pretrip-group-welcome', '行前1天-入群欢迎词', 'pre_trip_reminder', 'wechat_work_group', '欢迎来到美丽的新疆！我是您的专属AI小管家小琪，旅途中有需求随时联系。', 1, 1),
('tpl-ontrip-urumqi-day1', '落地首日-乌鲁木齐推荐', 'daily_reminder', 'wechat_work_group', '落地首日推荐：国际大巴扎、新疆美术馆、新疆古生态园；请注意时差和安保检查。', 1, 1),
('tpl-ontrip-morning-spring', '晨间提示-春季', 'daily_reminder', 'sms', '春季早晚温差大，请添衣保暖；上车后请全员系好安全带。', 1, 1),
('tpl-ontrip-morning-summer', '晨间提示-夏季', 'daily_reminder', 'sms', '夏季紫外线强，请防晒补水；上车后请全员系好安全带。', 1, 1),
('tpl-ontrip-morning-autumn', '晨间提示-秋季', 'daily_reminder', 'sms', '秋季清晨偏冷，请检查行李并增添外套；上车后请全员系好安全带。', 1, 1),
('tpl-ontrip-morning-winter', '晨间提示-冬季', 'daily_reminder', 'sms', '冬季低温路滑，请做好保暖与防滑；上车后请全员系好安全带。', 1, 1),
('tpl-ontrip-noon-rainy', '场景提示-雨天', 'risk_alert', 'wechat_work_group', '雨天道路湿滑，请备好雨具、减速慢行，优先选择室内就餐并及时更换干爽衣物。', 1, 1),
('tpl-ontrip-scene-horse', '场景提示-骑马', 'risk_alert', 'wechat_work_group', '请选择正规马队，检查骑具，按教练指导操作，不要靠近马后方。', 1, 1),
('tpl-ontrip-scene-ski', '场景提示-滑雪日', 'risk_alert', 'wechat_work_group', '滑雪前请准备防风保暖装备，佩戴头盔雪镜并充分热身。', 1, 1),
('tpl-ontrip-evening-preview', '晚间播报-次日行程', 'daily_reminder', 'wechat_work_group', '明日行程与天气提醒已更新，请按时集合，退房时带齐随身物品。', 1, 1),
('tpl-ontrip-issue-coordination', '行中协同-问题协调', 'risk_alert', 'wechat_work_group', '如遇酒店/车辆/景区问题，请在群内@管家和司导，我们将第一时间协调处理。', 1, 1),
('tpl-posttrip-survey', '下团满意度回访', 'satisfaction', 'sms', '感谢本次新疆之行，欢迎填写满意度问卷：{{survey_link}}。', 1, 1),
('tpl-posttrip-farewell', '下团欢送词', 'farewell', 'wechat_work_group', '感谢大家的陪伴与支持，祝一路平安，欢迎再来新疆！', 1, 1),
('tpl-posttrip-group-close', '解散群文案', 'farewell', 'wechat_work_group', '感谢同行，本群即将解散，感恩相伴，顺颂时祺。', 1, 1);

INSERT INTO t_notification_rule (rule_code, rule_name, stage, time_slot, scene, template_id, priority, enabled, conditions_json)
VALUES
('rule-pre-3day', '行前3天沟通提醒', 'pre_trip', 'morning', 'normal', 1, 10, 1, JSON_OBJECT('time_node', '出发前3天')),
('rule-pre-1day', '行前1天保险核查提醒', 'pre_trip', 'evening', 'normal', 2, 20, 1, JSON_OBJECT('time_node', '出发前1天')),
('rule-intrip-arrival', '落地当日本地指引', 'in_trip', 'afternoon', 'normal', 4, 30, 1, JSON_OBJECT('time_node', '游客落地乌鲁木齐当日')),
('rule-intrip-daily', '行中每日固定时段提醒', 'in_trip', 'all_day', 'normal', 12, 40, 1, JSON_OBJECT('time_node', '每日固定时段')),
('rule-intrip-scene', '特殊场景安全提醒', 'in_trip', 'afternoon', 'weather_alert', 9, 50, 1, JSON_OBJECT('time_node', '特殊游玩场景', 'scene_tags', JSON_ARRAY('骑马', '滑雪', '高原', '边境口岸', '极寒', '紫外线强'))),
('rule-posttrip-survey', '下团满意度调研', 'post_trip', 'evening', 'normal', 14, 60, 1, JSON_OBJECT('time_node', '下团即时'));

INSERT INTO t_notification_rule_channel (rule_id, channel, sort_order)
VALUES
(1, 'sms', 1),
(1, 'wechat_work_group', 2),
(2, 'wechat_work_group', 1),
(3, 'wechat_work_group', 1),
(4, 'wechat_work_group', 1),
(4, 'sms', 2),
(5, 'sms', 1),
(5, 'wechat_work_group', 2),
(6, 'sms', 1),
(6, 'email', 2);

INSERT INTO t_notification_task (task_code, trip_id, customer_id, notification_type, primary_channel, fallback_channel, rendered_content, idempotency_key, status, retry_count, max_retry, manual_intervention_required)
VALUES
('task-20260412-0001', 1, 'cust-1001', 'pre_trip_reminder', 'sms', 'wechat_work_group', '王敏，您的乌鲁木齐-喀纳斯精品线行程即将开始，请准时集合。', 'TEAM-DEMO-PRE:cust-1001:pre_trip_reminder:2026-05-05', 'sent', 0, 2, 0),
('task-20260412-0002', 2, 'cust-2001', 'daily_reminder', 'wechat_work_group', 'sms', '【今日提示】天气晴，注意防晒和补水。', 'TEAM-DEMO-ON:cust-2001:daily_reminder:2026-04-20-morning', 'sent', 1, 2, 0),
('task-20260412-0003', 3, 'cust-3001', 'satisfaction', 'sms', 'email', '感谢本次出行，欢迎填写满意度问卷。', 'TEAM-DEMO-POST:cust-3001:satisfaction:2026-03-16', 'manual_intervention', 2, 2, 1);

INSERT INTO t_notification_attempt (task_id, attempt_no, channel, ok, reason, provider_message, latency_ms, attempted_at)
VALUES
(1, 1, 'sms', 1, '', 'DELIVERED', 120, '2026-04-12 08:30:00'),
(2, 1, 'wechat_work_group', 0, 'rate_limit', '429 TOO MANY REQUESTS', 98, '2026-04-12 09:00:00'),
(2, 2, 'sms', 1, '', 'DELIVERED', 140, '2026-04-12 09:01:00'),
(3, 1, 'sms', 0, 'invalid_phone', '400 BAD REQUEST', 60, '2026-04-12 10:10:00'),
(3, 2, 'email', 0, 'smtp_timeout', 'TIMEOUT', 3000, '2026-04-12 10:13:00');
