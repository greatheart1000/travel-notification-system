from __future__ import annotations

import logging
import threading
from collections import defaultdict
from contextvars import ContextVar, Token
from typing import Any
from uuid import uuid4

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def new_trace_id() -> str:
    return uuid4().hex


def get_trace_id() -> str:
    return _trace_id_var.get()


def set_trace_id(value: str | None = None) -> str:
    trace_id = (value or "").strip() or new_trace_id()
    _trace_id_var.set(trace_id)
    return trace_id


def set_trace_context(value: str | None = None) -> tuple[str, Token[str]]:
    trace_id = (value or "").strip() or new_trace_id()
    return trace_id, _trace_id_var.set(trace_id)


def reset_trace_id(token: Token[str]) -> None:
    _trace_id_var.reset(token)


def mask_phone(phone: str) -> str:
    value = str(phone or "")
    if len(value) >= 7:
        return f"{value[:3]}****{value[-4:]}"
    return "***"


def mask_secret(value: str, *, keep: int = 4) -> str:
    raw = str(value or "")
    if len(raw) <= keep:
        return "***"
    return f"***{raw[-keep:]}"


class MetricsRegistry:
    """Small dependency-free metrics registry for counters and latency histograms."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)

    @staticmethod
    def _key(name: str, labels: dict[str, Any]) -> str:
        if not labels:
            return name
        rendered = ",".join(f"{key}={labels[key]}" for key in sorted(labels))
        return f"{name}{{{rendered}}}"

    def inc(self, name: str, value: float = 1.0, **labels: Any) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] += value

    def observe(self, name: str, value: float, **labels: Any) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._histograms[key].append(float(value))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            labeled_counters = dict(self._counters)
            counters: dict[str, float] = defaultdict(float)
            for key, value in labeled_counters.items():
                counters[key.split("{", 1)[0]] += value
            histograms: dict[str, dict[str, float]] = {}
            for key, values in self._histograms.items():
                if not values:
                    continue
                ordered = sorted(values)
                index = min(int(len(ordered) * 0.95), len(ordered) - 1)
                histograms[key] = {
                    "count": len(ordered),
                    "sum": round(sum(ordered), 3),
                    "min": round(ordered[0], 3),
                    "max": round(ordered[-1], 3),
                    "avg": round(sum(ordered) / len(ordered), 3),
                    "p95": round(ordered[index], 3),
                }
        return {
            "counters": dict(counters),
            "labeled_counters": labeled_counters,
            "histograms": histograms,
        }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()


metrics = MetricsRegistry()


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Emit a structured key=value log line with trace_id and basic PII masking."""
    safe_fields: dict[str, Any] = {}
    for key, value in fields.items():
        if key in {"phone", "customer_id", "mobile"} and isinstance(value, str):
            safe_fields[key] = mask_phone(value)
        elif key in {"token", "secret", "webhook_url"} and isinstance(value, str):
            safe_fields[key] = mask_secret(value)
        else:
            safe_fields[key] = value
    trace_id = get_trace_id()
    rendered = " ".join(f"{key}={safe_fields[key]}" for key in sorted(safe_fields))
    logger.log(level, "%s trace_id=%s %s", event, trace_id or "-", rendered)
