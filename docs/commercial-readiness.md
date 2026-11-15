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

---

## Commercial SaaS layer (2026-11-12)

The product now ships a deployable commercial layer on top of the notification
core. It is designed so that an operator only needs to fill `.env` and run
`docker compose up -d --build`.

### Self-service accounts and tenants
- Persistent tenants, users and sessions in MySQL (JSON store for local runs).
- Enterprise registration with SMS verification, password login, SMS-code login,
  SMS password reset, password change, and team-member management.
- PBKDF2 password hashing, opaque access/refresh tokens stored hashed,
  refresh-token rotation, logout revocation, login rate limiting, and last-admin
  protection.
- Tenant suspension and disabled-user tokens are rejected at request time.

### SMS
- Aliyun Dysmsapi SDK is a production dependency; templates are selected by
  purpose (`login`, `register`, `reset`).
- Per-phone 60s cooldown, daily per-phone/per-IP caps, global daily cap, and
  five-attempt verification limit.
- Debug verification codes are only returned with the mock provider or an
  explicit non-production flag.
- Tenant-level channel configuration controls WeCom webhook, SMS provider,
  sign name and business template code; credentials stay in the environment.

### Plans, payments and quota
- Built-in plans: free, trial, starter, growth, enterprise; prices and quotas
  are overridable via `BILLING_PLANS_JSON`.
- Trial subscription on tenant creation; expired subscriptions fall back to the
  free plan; quota is counted per business-timezone month.
- 易支付 / 极速付 (彩虹易支付 MD5 protocol) and Stripe Checkout adapters.
- Order state machine (`pending → paid/closed/refunded`), signature and amount
  verification, callback idempotency, advisory-lock settlement, late-callback
  recovery for locally closed orders, and pending-order capping.
- SMS quota is enforced in the provider registry; exhausted tenants fail closed
  and fall back to WeCom when configured.
- Payment receipts are sent by SMTP when a tenant contact email is configured.

### Platform operations
- `/operator` console (role `operator`): platform revenue, tenant list, manual
  plan activation and refund recording.
- Platform tenant is hidden from tenant lists and revenue.
- Registration, login failure, payment, refund, quota and verification metrics
  are exposed at `/api/health/metrics`.
- Production disables OpenAPI docs; `METRICS_TOKEN` optionally protects detail
  and metrics endpoints.

### Deployment
- Multi-stage `Dockerfile` builds the SPA and serves it from FastAPI.
- `docker-compose.yml` provides MySQL + app with healthchecks, automatic
  migrations and a non-root runtime user.
- `scripts/apply_migrations.py` is idempotent and tracks applied files.
- MySQL schema initialization and migration were verified in a real MySQL 8.2
  container, including rule creation, tenant config, payments, notification
  attempts/jobs and restart persistence.

### Remaining gaps before large-scale SaaS
1. Overall repository coverage is still below the notification-domain gate;
   billing/identity are covered by unit and API tests, but not every legacy
   module is. Targeted tests were added for weather, invoice profile, refund
   workflow and the worker entrypoint.
2. A dedicated worker entrypoint (`python -m app.worker`) and Compose `worker`
   service now own the scheduler/outbox; the web process defaults to
   `RUN_SCHEDULER=false`. Queue claiming still uses the advisory lock; MySQL
   row-level `SELECT ... FOR UPDATE SKIP LOCKED` remains the next scaling step.
3. Refunds now support a gateway attempt (Stripe Refunds API; Epay/Jisufu via a
   merchant-configured refund URL) and a tracked manual bookkeeping mode. The
   default is still manual bookkeeping; partial-refund UI and automatic
   reconciliation are not implemented.
4. Tenant invoice/tax fields are stored on the tenant profile. Subscription and
   trial expiry reminders (dunning) are implemented by the worker. Invoice PDF
   generation and self-service subscription cancellation beyond "cancel at
   period end" are not implemented.
5. MySQL row-level `SKIP LOCKED` claiming is still the next step for
   high-throughput multi-worker queues.
6. Stripe CNY availability depends on the merchant account; the adapter is
   implemented but should be validated against the live account.
7. A Playwright password-login smoke script (`scripts/e2e_smoke.py`) checks the
   main commercial pages. A full browser suite wired into CI is still pending.
8. Raw AK/SK and provider secrets still live in environment variables/secret
   manager; there is no dedicated secret-manager integration.
9. The region weather list API now exists and degrades to mock data when
   QWeather is not configured. Live weather still requires `QWEATHER_API_HOST`,
   `QWEATHER_API_KEY`, and tenant location configuration.

---

## Commercial hardening (2026-11-13)

- **Region weather API**: `GET /api/weather/{region}` uses QWeather when
  configured and deterministically falls back to mock data otherwise. The Trips
  page treats weather as non-blocking, so a weather outage no longer hides the
  trip list.
- **Tenant billing profile**: invoice title, tax id, registered address/phone,
  bank name/account and invoice email are stored on the tenant and editable at
  Settings → Notification Channels → Invoice info.
- **Refund workflow**: `manual` bookkeeping and `gateway` attempt modes with
  refund status/amount/reason/operator/error. Stripe uses the Refunds API;
  Epay/Jisufu use a merchant-configured refund URL. Gateway failures keep the
  order paid and surface the error in the operator console.
- **Dedicated worker**: `python -m app.worker` plus a Compose `worker` service
  own cron jobs and the outbox; the web process runs with `RUN_SCHEDULER=false`.
- **Dunning**: the worker scans trialing/paid subscriptions and sends
  idempotent expiry reminders at 7/3/1 days by email; operators can trigger a
  run manually.
- **E2E smoke**: `scripts/e2e_smoke.py` performs a password login and checks the
  main commercial pages with Playwright. It does not send SMS or payments.
- **Tests**: backend suite is at 194 passing tests (targeted coverage added for
  weather, invoice profile, refund workflow, dunning and the worker entrypoint).
