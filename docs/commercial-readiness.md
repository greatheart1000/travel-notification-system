# Commercial Readiness

This document records what is implemented for commercial/enterprise delivery, the
reliability semantics, and the remaining work before a SaaS/private deployment.

## Implemented

### Test isolation and TDD baseline
- `tests/conftest.py` blocks real TCP/`urllib` in every test.
- `tests/fakes.py` provides fake WeCom, SMS, weather, and audit implementations.
- Backend: 102 tests passing.
- Frontend: 8 contract tests passing; production build passes.
- Core notification-domain coverage gate: **85.67%** (CI fails below 85%).

### Multi-tenant isolation
- Trip repository supports tenant-scoped reads.
- Project notification config uses `(tenant_id, project_id)` as its logical key.
- Weather check, emergency weather, trip creation, notification history, rules, and
  risk evidence are tenant scoped.
- API test verifies that tenant B cannot read tenant A's trip or notification history.

### Reliability and idempotency
- Idempotency state machine: `sent` / `unknown` / retryable.
- Success marks `sent`; retryable failure leaves the key retryable; ambiguous
  timeout marks `unknown` and stops auto-retry to avoid duplicates.
- Dispatcher retries transient failures with bounded attempts; permanent errors
  (invalid phone, empty content, missing config) do not retry.
- Primary channel failure falls back to the configured fallback channel.
- Async dispatch jobs are persisted, reloaded after restart, retried with backoff,
  and moved to `manual_intervention` after max attempts.
- Queue processing is protected by a cross-process advisory lock (MySQL `GET_LOCK`,
  JSON backend `flock`) so multiple workers do not send the same job twice in a tick.
- Risk-notification evidence is updated on retry instead of permanently blocking
  a failed send.

### Configuration and decoupling
- No hardcoded WeCom webhook key.
- WeCom provider fails closed when no webhook is configured and only accepts
  official `qyapi.weixin.qq.com` webhook URLs.
- SMS provider fails closed unless `SMS_PROVIDER` is explicitly configured.
- Per-tenant channel configuration is stored in `t_tenant_notification_config`
  and can be managed via `GET/PUT /api/admin/tenant-notification-config`.
- Per-trip webhook, per-project SMS sign/template code, and per-role recipients.
- Notification rules gate the scheduler: no rules = legacy behavior; matching
  rules = allow; configured-but-unmatched rules = skip with audit.
- Role recipients can be configured as:
  ```json
  {
    "role_recipients": {
      "manager": {"channel": "sms", "address": "138..."},
      "concierge": {"channel": "sms", "address": "139..."},
      "driver": {"channel": "wechat_work_group", "address": "https://qyapi.weixin.qq.com/..."}
    }
  }
  ```
  When explicit recipients exist, a missing role is skipped, not routed to the
  shared group.

### Observability
- `X-Trace-Id` middleware and propagation to task/attempt records.
- Structured log helper with phone/webhook masking.
- `GET /api/health/metrics` exposes counters and latency histograms.
- `GET /api/health/detail` exposes queue backlog and component status.

### Migration and deployment
- `docs/migrations/2026-11-05-commercial-notification.sql` adds:
  - `trace_id` columns;
  - durable `t_notification_job` outbox;
  - durable `t_notification_idempotency` state table;
  - dead-letter view;
  - normalized role-recipient table;
  - tenant-scoped indexes.
- CI runs backend tests/coverage, frontend contract tests, and production build.

## Remaining before full SaaS/private commercial release

1. **Overall repository coverage is ~51%**, while the notification domain is 86%.
   Analytics, preference, agent-generation, orchestrator, and MySQL persistence
   paths still need tests.
2. **MySQL outbox code path** is represented by the migration and advisory-lock
   serialization. A dedicated row-level `SELECT ... FOR UPDATE SKIP LOCKED`
   repository is the next step for high-throughput multi-worker deployments.
3. **Per-tenant provider credentials** are supported at config level (webhook,
   SMS provider/sign/template, credential id). Raw AK/SK still belong in the
   environment/secret manager; a dedicated secret-manager integration remains.
4. **Exactly-once is impossible with WeCom group robots** (no idempotency key).
   The chosen policy is at-least-once with local idempotency and manual review on
   ambiguous timeout. This must be accepted as a business trade-off.
5. **Frontend notification send flow** now calls the real API, but end-to-end
   browser coverage (Playwright) is not yet added.
6. **Legacy code cleanup** removed the old BFF/event bus/duplicate scheduler and
   unmounted routes; remaining unused repositories should be removed after the
   next migration.
7. **MySQL migration runner** is a SQL file, not an automated/versioned migration
   tool. Production should run it through the deployment pipeline with backups.
