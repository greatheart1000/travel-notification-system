from __future__ import annotations

import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)

WECHAT_WEBHOOK_URL = os.getenv(
    "WECHAT_WEBHOOK_URL",
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=5caf181b-1b65-4c28-8e68-e2f8788df1fc",
)

# 线程池用于异步 HTTP 调用（避免阻塞主线程）
_webhook_executor = ThreadPoolExecutor(max_workers=8)


class WeChatWorkWebhookProvider:
    """企业微信群机器人 Webhook 推送，支持同步和异步发送。"""

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url or WECHAT_WEBHOOK_URL

    def _do_send(self, customer_id: str, content: str) -> tuple[bool, str]:
        """同步 HTTP 发送（在 executor 中运行）。"""
        import urllib.request
        import urllib.error

        if not content.strip():
            return False, "empty_content"
        payload = json.dumps(
            {"msgtype": "text", "text": {"content": content}},
            ensure_ascii=False,
        ).encode("utf-8")
        try:
            req = urllib.request.Request(
                self.webhook_url,
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
        return self._do_send(customer_id, content)

    async def send_async(self, customer_id: str, content: str) -> tuple[bool, str]:
        """异步发送 — 不阻塞主线程。"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_webhook_executor, self._do_send, customer_id, content)


class WeChatWorkProvider:
    """保留旧接口兼容（群管理操作）。"""

    def dismiss_group(self, team_id: str) -> dict[str, Any]:
        logger.info("[WeCom] dismiss_group team_id=%s (mock)", team_id)
        return {"ok": True, "team_id": team_id, "action": "dissolve", "message": "success"}

    def send_group_message(self, team_id: str, content: str) -> dict[str, Any]:
        provider = WeChatWorkWebhookProvider()
        ok, msg = provider.send(team_id, content)
        return {"ok": ok, "message": msg}
