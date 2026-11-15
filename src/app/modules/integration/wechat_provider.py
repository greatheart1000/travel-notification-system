from __future__ import annotations

import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

WECHAT_WEBHOOK_URL = os.getenv("WECHAT_WEBHOOK_URL", "")

# 线程池用于异步 HTTP 调用（避免阻塞主线程）
_webhook_executor = ThreadPoolExecutor(max_workers=8)


class WeChatWorkWebhookProvider:
    """企业微信群机器人 Webhook 推送，支持同步和异步发送。"""

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url or os.getenv("WECHAT_WEBHOOK_URL", WECHAT_WEBHOOK_URL)

    @staticmethod
    def _is_valid_webhook_url(url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname == "qyapi.weixin.qq.com"
            and parsed.path.rstrip("/") == "/cgi-bin/webhook/send"
            and bool(parse_qs(parsed.query).get("key"))
        )

    def _resolve_webhook_url(self, provider_context: dict[str, str] | None = None) -> str:
        context = provider_context or {}
        return str(context.get("webhook_url") or self.webhook_url or "").strip()

    def _do_send(
        self,
        customer_id: str,
        content: str,
        webhook_url: str | None = None,
    ) -> tuple[bool, str]:
        """同步 HTTP 发送（在 executor 中运行）。"""
        import urllib.error
        import urllib.request

        if not content.strip():
            return False, "empty_content"
        target_url = webhook_url or self.webhook_url
        payload = json.dumps(
            {"msgtype": "text", "text": {"content": content}},
            ensure_ascii=False,
        ).encode("utf-8")
        try:
            req = urllib.request.Request(
                target_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            if body.get("errcode") == 0:
                logger.info("[WeChatWebhook] sent ok, customer=%s", customer_id)
                return True, "ok"
            errmsg = body.get("errmsg", "unknown")
            logger.warning("[WeChatWebhook] errcode=%s errmsg=%s", body.get("errcode"), errmsg)
            return False, f"wecom_error:{errmsg}"
        except urllib.error.URLError as exc:
            logger.error("[WeChatWebhook] request failed: %s", exc)
            return False, f"request_failed:{exc}"

    def send(
        self,
        customer_id: str,
        content: str,
        provider_context: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        """同步发送（兼容旧调用）。"""
        target_url = self._resolve_webhook_url(provider_context)
        if not target_url:
            return False, "wechat_webhook_not_configured"
        if not self._is_valid_webhook_url(target_url):
            return False, "invalid_webhook_url"
        return self._do_send(customer_id, content, target_url)

    async def send_async(
        self,
        customer_id: str,
        content: str,
        provider_context: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        """异步发送 — 不阻塞主线程。"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _webhook_executor,
            self.send,
            customer_id,
            content,
            provider_context,
        )


class WeChatWorkProvider:
    """保留旧接口兼容（群管理操作）。"""

    def dismiss_group(self, team_id: str) -> dict[str, Any]:
        logger.info("[WeCom] dismiss_group team_id=%s (mock)", team_id)
        return {"ok": True, "team_id": team_id, "action": "dissolve", "message": "success"}

    def send_group_message(self, team_id: str, content: str) -> dict[str, Any]:
        provider = WeChatWorkWebhookProvider()
        ok, msg = provider.send(team_id, content)
        return {"ok": ok, "message": msg}


def get_wechat_provider_for_trip(trip: dict[str, Any] | None) -> WeChatWorkWebhookProvider:
    """Resolve the trip-level webhook first, then the environment default."""
    webhook_url = str((trip or {}).get("webhook_url") or "").strip()
    return WeChatWorkWebhookProvider(webhook_url=webhook_url or None)
