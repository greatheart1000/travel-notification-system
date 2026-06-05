from __future__ import annotations

import logging
import os
from typing import Any

import urllib.request
import urllib.error
import json

logger = logging.getLogger(__name__)

WECHAT_WEBHOOK_URL = os.getenv(
    "WECHAT_WEBHOOK_URL",
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=5caf181b-1b65-4c28-8e68-e2f8788df1fc",
)


class WeChatWorkWebhookProvider:
    """企业微信群机器人 Webhook 推送，实现 ChannelProvider 协议。"""

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url or WECHAT_WEBHOOK_URL

    def send(
        self,
        customer_id: str,
        content: str,
        provider_context: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
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


class WeChatWorkProvider:
    """保留旧接口兼容（群管理操作）。"""

    def dismiss_group(self, team_id: str) -> dict[str, Any]:
        logger.info("[WeCom] dismiss_group team_id=%s (mock)", team_id)
        return {"ok": True, "team_id": team_id, "action": "dissolve", "message": "success"}

    def send_group_message(self, team_id: str, content: str) -> dict[str, Any]:
        provider = WeChatWorkWebhookProvider()
        ok, msg = provider.send(team_id, content)
        return {"ok": ok, "message": msg}
