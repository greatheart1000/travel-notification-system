# Frontend Handoff

Updated: 2026-04-11 (Asia/Shanghai)
Scope: frontend handoff readiness based on current code and smoke results.

## 1) Page Readiness

| Page | Status | Notes |
|---|---|---|
| Dashboard | ready | Uses typed API + adapter; supports `loading/error/empty/retry`. |
| Trips | ready | List/create/update/delete wired to typed API; supports `loading/error/empty/retry`. |
| Notifications | partial | Template list + send are wired; template creation is not persisted (backend endpoint not available in current flow). |
| Analytics | ready | Metrics/channels/top-trips wired to typed API; supports `loading/error/empty/retry`. |
| Preferences | ready | Real backend read/write enabled with fallback strategy; supports `loading/error/empty/retry`. |

## 2) Backend Dependency Matrix

| Domain | Endpoint | Method | Frontend Use |
|---|---|---|---|
| Auth | `/api/auth/login` | POST | Login gate in app shell |
| Auth | `/api/auth/logout` | POST | Logout cleanup |
| Auth | `/api/users/me` | GET | Login-state validation |
| Dashboard | `/api/dashboard/stats` | GET | KPI cards |
| Dashboard | `/api/notifications/recent?limit=10` | GET | Recent notification table |
| Trips | `/api/trips` | GET | Trip list |
| Trips | `/api/trips` | POST | Create trip |
| Trips | `/api/trips/{id}` | PUT | Update trip status/details |
| Trips | `/api/trips/{id}` | DELETE | Delete trip |
| Notifications | `/api/notifications/templates` | GET | Template list |
| Notifications | `/api/notifications/send` | POST | Manual send |
| Analytics | `/api/analytics/metrics` | GET | Metrics + channel performance + top trips |
| Preferences | `/api/preferences/me` | GET/PUT | Preferred endpoint for read/write |
| Preferences | `/api/preferences` | GET/PUT | Fallback when `/preferences/me` returns 404 |

## 3) Minimal Regression Path

1. Open app: unauthenticated users should see login gate.
2. Login with valid credentials (`admin/123456` in current dev data).
3. Dashboard loads stats and recent notifications; retry works when in error state.
4. Trips page: create one trip, mark one as completed, delete one; state feedback should be visible.
5. Notifications page: template list loads; click send on one template and verify success/failure message is visible.
6. Analytics page: metrics table/cards render; retry and empty states are recoverable.
7. Preferences page: load from backend, change values, save, reload page, verify values are mapped back from API.
8. Logout from header: token is cleared and app returns to login gate.

## 4) Known Limits and User Impact

1. Notification template creation is currently not persisted in backend path used by frontend.
   - User impact: "Create template" dialog behaves as local draft/placeholder flow, not real server-side creation.
2. Contract is still in compatibility mode for field/value variants.
   - User impact: none directly; adapter currently absorbs `team/team_id`, channel variants, and mixed enum styles.
3. 401 handling is centralized in API interceptor and app auth event handling.
   - User impact: when token expires/invalidates, user is logged out and must re-login.

## 5) Follow-up Integration Points

1. Backend-template CRUD alignment
   - Add/confirm template creation endpoint contract and wire create action from Notifications page.
2. Contract convergence cleanup
   - Gradually remove compatibility aliases once backend stabilizes canonical fields (`team_id`, channel code enums, status enums).
3. Auth scope hardening
   - If backend makes more endpoints protected, keep current centralized 401 handling and add targeted UX messaging if needed.
4. Test depth expansion (post core flow)
   - Add API/adapters unit tests and page smoke tests when full contract/regression phase starts.

## 6) Smoke Result Snapshot

- `npm -C frontend run build`: PASS
- Runtime sanity: `npm -C frontend run dev -- --host 127.0.0.1 --port 5174 --strictPort` starts successfully (Vite ready log observed).
