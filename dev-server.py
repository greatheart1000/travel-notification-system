#!/usr/bin/env python3
"""Travel Hub 本地联调入口。

支持能力：
- `up`: 一键启动后端 + 前端
- `health`: 健康检查
- `smoke`: 真实 HTTP smoke 校验（可自动拉起后端）
- `verify`: 契约测试 + 关键链路测试（可选附带 smoke）
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = REPO_ROOT / "frontend"
BACKEND_BASE = "http://127.0.0.1:8000"
API_BASE = f"{BACKEND_BASE}/api"


def _print(title: str) -> None:
    print(f"\n[dev-server] {title}")


def _run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    _print(f"run: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=cwd, env=env)
    return proc.returncode


def _http_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 8.0,
) -> tuple[int, dict[str, Any]]:
    body = None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    request = Request(f"{API_BASE}{path}", data=body, method=method, headers=req_headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as err:
        raw = err.read().decode("utf-8")
        parsed: dict[str, Any] = {}
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"raw": raw}
        return err.code, parsed
    except URLError as err:
        raise RuntimeError(f"API 不可达: {err}") from err


def check_health(verbose: bool = True) -> bool:
    try:
        status, body = _http_json("GET", "/health")
    except RuntimeError:
        if verbose:
            print("[health] backend unreachable")
        return False

    ok = status == 200 and body.get("code") == 200 and body.get("data", {}).get("status") == "ok"
    if verbose:
        if ok:
            print("[health] OK")
        else:
            print(f"[health] FAIL status={status} body={body}")
    return ok


def wait_for_health(timeout_seconds: float = 25.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if check_health(verbose=False):
            return True
        time.sleep(1)
    return False


def start_backend() -> subprocess.Popen[str]:
    env = os.environ.copy()
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{env['PYTHONPATH']}" if env.get("PYTHONPATH") else src_path
    )
    _print("start backend: python -m app.main")
    return subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
    )


def start_frontend() -> subprocess.Popen[str]:
    _print("start frontend: ./start.sh dev --skip-api-check")
    return subprocess.Popen(
        ["bash", "start.sh", "dev", "--skip-api-check"], cwd=FRONTEND_DIR, text=True
    )


def terminate_process(proc: subprocess.Popen[str], name: str) -> None:
    if proc.poll() is not None:
        return
    _print(f"stop {name}")
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()


def run_smoke() -> bool:
    _print(
        "smoke: /health -> /auth/login -> /users/me -> /trips -> /notifications/send -> /analytics/metrics"
    )

    health_status, health_body = _http_json("GET", "/health")
    if not (health_status == 200 and health_body.get("code") == 200):
        print(f"[smoke] health failed: {health_status}, {health_body}")
        return False

    login_status, login_body = _http_json(
        "POST",
        "/auth/login",
        {"username": "admin", "password": "123456"},
    )
    if login_status != 200:
        print(f"[smoke] login failed: {login_status}, {login_body}")
        return False

    token = login_body.get("data", {}).get("access_token")
    if not token:
        print(f"[smoke] login missing token: {login_body}")
        return False

    auth_headers = {"Authorization": f"Bearer {token}"}

    me_status, me_body = _http_json("GET", "/users/me", headers=auth_headers)
    if not (me_status == 200 and me_body.get("data", {}).get("username") == "admin"):
        print(f"[smoke] /users/me failed: {me_status}, {me_body}")
        return False

    trips_status, trips_body = _http_json("GET", "/trips", headers=auth_headers)
    if not (trips_status == 200 and "items" in trips_body.get("data", {})):
        print(f"[smoke] /trips failed: {trips_status}, {trips_body}")
        return False

    send_status, send_body = _http_json(
        "POST",
        "/notifications/send",
        {"customer_name": "smoke", "trip": "smoke"},
        headers=auth_headers,
    )
    if not (send_status == 200 and send_body.get("data", {}).get("ok") is True):
        print(f"[smoke] /notifications/send failed: {send_status}, {send_body}")
        return False

    metrics_status, metrics_body = _http_json("GET", "/analytics/metrics", headers=auth_headers)
    if not (metrics_status == 200 and "metrics" in metrics_body.get("data", {})):
        print(f"[smoke] /analytics/metrics failed: {metrics_status}, {metrics_body}")
        return False

    print("[smoke] OK")
    return True


def run_full_tests() -> int:
    # 契约测试：HTTP 层 API 行为
    contract_rc = _run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_http_api.py"], cwd=REPO_ROOT
    )
    if contract_rc != 0:
        return contract_rc

    # 关键链路：通知、触发、审计、生命周期、演示引导
    return _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_bootstrap.py",
            "tests/test_notification_pipeline.py",
            "tests/test_trigger_and_audit.py",
            "tests/test_lifecycle_rule_builder.py",
            "tests/test_concierge_playbook.py",
        ],
        cwd=REPO_ROOT,
    )


def verify(full_tests: bool) -> int:
    # 默认仅做最小联调校验，优先保证主链路可运行。
    smoke_rc = smoke(spawn_backend=True)
    if smoke_rc != 0:
        return smoke_rc

    if not full_tests:
        print("[verify] minimal smoke checks passed")
        return 0

    _print("run full pytest suites")
    return run_full_tests()


def up() -> int:
    backend_proc = start_backend()
    frontend_proc: subprocess.Popen[str] | None = None
    try:
        if not wait_for_health():
            print("[up] backend 启动失败或健康检查超时")
            return 1

        frontend_proc = start_frontend()
        _print("backend:  http://127.0.0.1:8000")
        _print("frontend: http://127.0.0.1:5173")
        _print("Ctrl+C 结束")

        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("[up] backend 已退出")
                return backend_proc.returncode or 1
            if frontend_proc.poll() is not None:
                print("[up] frontend 已退出")
                return frontend_proc.returncode or 1
    except KeyboardInterrupt:
        return 0
    finally:
        if frontend_proc is not None:
            terminate_process(frontend_proc, "frontend")
        terminate_process(backend_proc, "backend")


def smoke(spawn_backend: bool) -> int:
    backend_proc: subprocess.Popen[str] | None = None
    try:
        if not check_health(verbose=False):
            if not spawn_backend:
                print("[smoke] backend 未运行，请先启动或使用 --spawn-backend")
                return 1
            backend_proc = start_backend()
            if not wait_for_health():
                print("[smoke] backend 自动启动失败")
                return 1
        return 0 if run_smoke() else 1
    finally:
        if backend_proc is not None:
            terminate_process(backend_proc, "backend")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Travel Hub 联调工具")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    subparsers.add_parser("up", help="一键启动后端和前端")
    subparsers.add_parser("health", help="检查 /api/health")

    smoke_parser = subparsers.add_parser("smoke", help="执行 HTTP smoke 校验")
    smoke_parser.add_argument(
        "--spawn-backend",
        action="store_true",
        help="当 backend 未运行时自动拉起后再 smoke",
    )

    verify_parser = subparsers.add_parser("verify", help="执行最小联调校验（默认 smoke）")
    verify_parser.add_argument(
        "--full-tests",
        action="store_true",
        help="在 smoke 通过后，继续执行 pytest 契约/关键链路测试",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.cmd == "up":
        return up()
    if args.cmd == "health":
        return 0 if check_health(verbose=True) else 1
    if args.cmd == "smoke":
        return smoke(spawn_backend=args.spawn_backend)
    if args.cmd == "verify":
        return verify(full_tests=args.full_tests)
    return 1


if __name__ == "__main__":
    sys.exit(main())
