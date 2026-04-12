---
name: travel-notification-requirements
description: Extract and consolidate business requirements for travel-operation notification systems from mixed source materials (DOCX process docs, XLSX execution tables, clarification question lists, and existing project docs). Use when the user asks to define MVP/P1/P2 scope, role collaboration flow, trigger rules, channel fallback strategy, acceptance metrics, or to generate a formal requirements specification for itinerary pre-trip/in-trip/post-trip operations.
---

# Travel Notification Requirements Skill

## Overview
Generate a consistent requirements package for tourism operations automation projects.
Focus on the lifecycle of itinerary service delivery: pre-trip, in-trip, and post-trip.

## Workflow
1. Collect source artifacts
- Required minimum: one operational process document.
- Preferred set: process DOCX + execution XLSX + clarification-question list DOCX.
- Optional: existing `docs/*.md`, API contracts, runbooks.

2. Build a normalized event matrix
- Convert unstructured content into entries with:
  - `stage` (pre-trip/in-trip/post-trip)
  - `time_node` (T-3d, T-1d, daily morning/noon/evening, special event, post-trip)
  - `trigger_type` (mandatory/scheduled/conditional/manual)
  - `trigger_source` (itinerary tag/weather API/manual checkbox/system state)
  - `actor` (system/concierge/guide/customer-service/sales/admin)
  - `channel` (SMS/enterprise chat/group message/phone form link)
  - `fallback` (retry/escalate/manual intervention)
  - `audit_key` (who/when/to-whom/template/version/result)

3. Generate requirement specification
- Use `references/requirement-outline.md` as the default structure.
- Explicitly include:
  - Business objectives and non-goals
  - Role boundaries and responsibility handoff
  - Notification orchestration and fallback policy
  - Template governance and review/audit requirements
  - Data sources and integration boundaries
  - Acceptance KPIs and observability metrics
  - P0/P1/P2 phased scope

4. Produce decision gaps
- Convert unresolved clarification questions into a prioritized decision list:
  - `P0 must decide before development`
  - `P1 can decide during UAT`
  - `P2 roadmap`

5. Align to codebase modules
- Map requirements into repository domains when present:
  - `trigger` for rule evaluation and schedule/condition triggers
  - `notification` for template rendering, dispatch, retries, fallback
  - `complaint` for escalation events
  - `survey` for post-trip satisfaction loop
  - `audit` for accountability and traceability
  - `integration` for external systems (weather/order/CRM/channel gateways)

## Output Contract
When this skill is applied, output should include:
1. A formal requirements document (`docs/*.md`).
2. A concise "what system to build" summary (architecture + core workflows).
3. A prioritized unresolved-decision list.

## Quality Gate
Before finalizing, verify the requirements include all of these:
- Pre-trip, in-trip, and post-trip lifecycle coverage.
- Mandatory nodes vs conditional triggers.
- Seasonal/weather/special-activity safety scenarios.
- Channel failure handling and manual takeover policy.
- Role-based permissions and auditability.
- Measurable acceptance KPIs.

## References
- Requirement outline: `references/requirement-outline.md`
