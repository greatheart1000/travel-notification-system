#!/usr/bin/env python3
"""Playwright smoke test for the commercial UI.

Start the backend and frontend first, then run:

    E2E_PASSWORD=<admin password> python3 scripts/e2e_smoke.py \
        --base-url http://127.0.0.1:5173

The script signs in with a password (no SMS/payment calls), visits the main
commercial pages, and fails on page errors or non-empty browser console errors.
"""

from __future__ import annotations

import argparse
import os
import sys

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

DEFAULT_PAGES = [
    ("/trips", "行程管理"),
    ("/analytics", "数据分析"),
    ("/billing", "套餐与账单"),
    ("/preferences", "偏好设置"),
    ("/settings/rules", "通知规则"),
    ("/settings/channels", "通知渠道配置"),
]


def _fail(message: str) -> None:
    print(f"[e2e] FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def _wait_for_text(page: Page, text: str, timeout: int = 15_000) -> None:
    try:
        page.get_by_text(text, exact=False).first.wait_for(timeout=timeout)
    except PlaywrightError:
        _fail(f"expected text not found: {text} (url={page.url})")


def run(args: argparse.Namespace) -> None:
    if not args.password:
        _fail("E2E_PASSWORD is required (use BOOTSTRAP_ADMIN_PASSWORD)")
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        page.goto(f"{args.base_url}/login", wait_until="networkidle")
        _wait_for_text(page, "登录企业工作台")
        page.get_by_placeholder("请输入用户名").fill(args.username)
        page.get_by_placeholder("请输入密码").fill(args.password)
        page.get_by_role("button", name="登录", exact=True).click()
        page.wait_for_url("**/trips", timeout=20_000)
        _wait_for_text(page, "行程管理")

        for path, heading in DEFAULT_PAGES:
            page.goto(f"{args.base_url}{path}", wait_until="networkidle")
            _wait_for_text(page, heading)

        browser.close()

    if page_errors:
        _fail("page errors:\n" + "\n".join(page_errors))
    if console_errors:
        _fail("console errors:\n" + "\n".join(console_errors))

    print(f"[e2e] OK: {len(DEFAULT_PAGES)} pages checked at {args.base_url}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Commercial UI Playwright smoke test")
    parser.add_argument(
        "--base-url",
        default=os.getenv("E2E_BASE_URL", "http://127.0.0.1:5173"),
        help="Frontend base URL (default: E2E_BASE_URL or http://127.0.0.1:5173)",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("E2E_USERNAME", "admin"),
        help="Login username (default: E2E_USERNAME or admin)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("E2E_PASSWORD", ""),
        help="Login password (default: E2E_PASSWORD)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=os.getenv("E2E_HEADED", "").lower() in {"1", "true", "yes"},
        help="Run a visible browser window",
    )
    run(parser.parse_args())


if __name__ == "__main__":
    main()
