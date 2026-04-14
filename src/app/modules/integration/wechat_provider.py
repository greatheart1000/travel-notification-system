from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class WeChatWorkProvider:
    def dismiss_group(self, team_id: str) -> dict[str, Any]:
        """模拟解散企业微信群逻辑"""
        print(f"\n[MOCK WECOM] >>> DISMISSING GROUP: {team_id}")
        print(f"[MOCK WECOM] >>> STATUS: Group {team_id} has been dissolved.\n")

        return {"ok": True, "team_id": team_id, "action": "dissolve", "message": "success"}

    def send_group_message(self, team_id: str, content: str) -> dict[str, Any]:
        """模拟发送企微群消息"""
        print(f"\n[MOCK WECOM] >>> SENDING TO GROUP: {team_id}")
        print(f"[MOCK WECOM] >>> CONTENT: {content}\n")
        return {"ok": True}
