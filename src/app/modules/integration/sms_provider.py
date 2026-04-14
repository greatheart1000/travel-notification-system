from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class SMSProvider(ABC):
    @abstractmethod
    def send_sms(self, phone: str, content: str, sign_name: str = "TravelHub") -> dict[str, Any]:
        """发送短信接口"""
        pass


class MockSMSProvider(SMSProvider):
    def send_sms(self, phone: str, content: str, sign_name: str = "TravelHub") -> dict[str, Any]:
        # MVP 阶段模拟发送，直接在控制台输出
        print(f"\n[MOCK SMS] >>> SENDING TO: {phone}")
        print(f"[MOCK SMS] >>> SIGN: 【{sign_name}】")
        print(f"[MOCK SMS] >>> CONTENT: {content}\n")

        return {"ok": True, "msg_id": f"mock-msg-{phone[-4:]}", "status": "sent"}


class AliyunSMSProvider(SMSProvider):
    def send_sms(self, phone: str, content: str, sign_name: str = "TravelHub") -> dict[str, Any]:
        # 未来对接阿里云的占位符
        logger.info(f"Aliyun SMS sending logic would go here for {phone}")
        return {"ok": False, "error": "Aliyun SMS not configured"}
