-- Commercial notification hardening migration
-- Target: MySQL 8.0+
-- Apply once per environment before deploying the refactored notification service.
-- The application still supports the JSON backend for local/demo use.

-- ---------------------------------------------------------------------------
-- 1) Traceability on notification tasks/attempts
-- ---------------------------------------------------------------------------
ALTER TABLE t_notification_task
  ADD COLUMN trace_id VARCHAR(64) NOT NULL DEFAULT '' AFTER idempotency_key,
  ADD KEY idx_task_tenant_trace (tenant_id, trace_id);

ALTER TABLE t_notification_attempt
  ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT 'tenant-a' AFTER task_id,
  ADD COLUMN trace_id VARCHAR(64) NOT NULL DEFAULT '' AFTER latency_ms,
  ADD KEY idx_attempt_tenant_trace (tenant_id, trace_id),
  ADD KEY idx_attempt_tenant_time (tenant_id, attempted_at);

-- ---------------------------------------------------------------------------
-- 2) Durable async dispatch outbox
-- One row per queued notification job. Workers claim a row by moving it to
-- 'processing' with a lease; other instances skip it until the lease expires.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS t_notification_job (
  job_id VARCHAR(64) NOT NULL,
  tenant_id VARCHAR(64) NOT NULL,
  team_id VARCHAR(64) NOT NULL DEFAULT '',
  trip_id VARCHAR(64) NOT NULL DEFAULT '',
  task_id VARCHAR(64) NOT NULL,
  channel VARCHAR(32) NOT NULL DEFAULT 'sms',
  status ENUM('pending','processing','retrying','sent','failed','manual_intervention')
    NOT NULL DEFAULT 'pending',
  attempt INT UNSIGNED NOT NULL DEFAULT 0,
  max_attempt INT UNSIGNED NOT NULL DEFAULT 3,
  next_run_at DATETIME(6) NOT NULL,
  lease_until DATETIME(6) NULL,
  worker_id VARCHAR(128) NOT NULL DEFAULT '',
  last_error VARCHAR(512) NOT NULL DEFAULT '',
  payload JSON NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (job_id),
  KEY idx_job_due (status, next_run_at),
  KEY idx_job_tenant_status (tenant_id, status),
  KEY idx_job_task (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------------
-- 3) Durable idempotency state machine
-- status: sent | unknown. 'unknown' means a timeout/ambiguous failure occurred;
-- it must not be auto-retried because the provider may have accepted it.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS t_notification_idempotency (
  idempotency_key VARCHAR(255) NOT NULL,
  tenant_id VARCHAR(64) NOT NULL DEFAULT '',
  status ENUM('sent','unknown') NOT NULL,
  task_id VARCHAR(64) NOT NULL DEFAULT '',
  provider_message VARCHAR(512) NOT NULL DEFAULT '',
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (idempotency_key),
  KEY idx_idem_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------------
-- 4) Dead-letter view for operations
-- Rows are derived from jobs that exhausted retries or need manual review.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_notification_dead_letter AS
SELECT
  job_id,
  tenant_id,
  team_id,
  trip_id,
  task_id,
  channel,
  status,
  attempt,
  last_error,
  next_run_at,
  updated_at
FROM t_notification_job
WHERE status IN ('failed', 'manual_intervention');

-- ---------------------------------------------------------------------------
-- 5) Optional role recipient routing table
-- The application currently reads role_recipients from trip/project config
-- (JSON/MySQL ext_data). This table is the normalized target for the next
-- migration step and can be used by private deployments that need per-role
-- webhook/phone routing.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS t_trip_role_recipient (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id VARCHAR(64) NOT NULL,
  trip_id VARCHAR(64) NOT NULL,
  role ENUM('manager','concierge','driver') NOT NULL,
  channel ENUM('sms','wechat_work_group') NOT NULL DEFAULT 'wechat_work_group',
  address VARCHAR(512) NOT NULL,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_trip_role (tenant_id, trip_id, role),
  KEY idx_role_recipient_trip (tenant_id, trip_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------------
-- 6) Tenant-scoped uniqueness/index hardening
-- Wrap these in a migration runner that checks information_schema first if
-- your environment already has equivalent indexes.
-- ---------------------------------------------------------------------------
ALTER TABLE t_trip
  ADD KEY idx_trip_tenant_status_start (tenant_id, status, start_date);

ALTER TABLE t_notification_template
  ADD UNIQUE KEY uk_template_tenant_code_version (tenant_id, template_code, version);

ALTER TABLE t_notification_rule
  ADD UNIQUE KEY uk_rule_tenant_code (tenant_id, rule_code);
