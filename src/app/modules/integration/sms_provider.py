from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class SMSProvider(ABC):
    @abstractmethod
    def send_sms(
        self,
        phone: str,
        content: str,
        sign_name: str = "TravelHub",
        template_code: str = "",
        template_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """发送短信接口"""
        pass


class MockSMSProvider(SMSProvider):
    def send_sms(
        self,
        phone: str,
        content: str,
        sign_name: str = "TravelHub",
        template_code: str = "",
        template_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # MVP 阶段模拟发送，直接在控制台输出
        print(f"\n[MOCK SMS] >>> SENDING TO: {phone}")
        print(f"[MOCK SMS] >>> SIGN: 【{sign_name}】")
        if template_code:
            print(f"[MOCK SMS] >>> TEMPLATE_CODE: {template_code}")
        if template_params:
            print(f"[MOCK SMS] >>> TEMPLATE_PARAMS: {template_params}")
        print(f"[MOCK SMS] >>> CONTENT: {content}\n")

        return {"ok": True, "msg_id": f"mock-msg-{phone[-4:]}", "status": "sent"}


class AliyunSMSProvider(SMSProvider):
    def __init__(self):
        try:
            from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
            from alibabacloud_tea_openapi import models as open_api_models
        except ImportError:
            raise RuntimeError("alibabacloud_dysmsapi20170525 is not installed")

        access_key_id = os.getenv("ALIYUN_SMS_AK", "")
        access_key_secret = os.getenv("ALIYUN_SMS_SK", "")

        config = open_api_models.Config(
            access_key_id=access_key_id, access_key_secret=access_key_secret
        )
        config.endpoint = "dysmsapi.aliyuncs.com"
        self.client = Dysmsapi20170525Client(config)

    def send_sms(
        self,
        phone: str,
        content: str,
        sign_name: str = "TravelHub",
        template_code: str = "",
        template_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
        from alibabacloud_tea_util import models as util_models

        template_code = template_code or os.getenv("ALIYUN_SMS_TEMPLATE_CODE", "SMS_DEFAULT")

        payload = template_params or {"content": content[:20]}
        template_param = json.dumps(payload, ensure_ascii=False)

        send_sms_request = dysmsapi_20170525_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=sign_name,
            template_code=template_code,
            template_param=template_param,
        )
        runtime = util_models.RuntimeOptions()

        try:
            response = self.client.send_sms_with_options(send_sms_request, runtime)
            body = response.body
            if body.code == "OK":
                return {"ok": True, "msg_id": body.biz_id, "status": "sent"}
            else:
                logger.error(f"Aliyun SMS Error: {body.code} - {body.message}")
                return {"ok": False, "error": body.message}
        except Exception as e:
            logger.error(f"Aliyun SMS Exception: {str(e)}")
            return {"ok": False, "error": str(e)}


def get_sms_provider() -> SMSProvider:
    provider_type = os.getenv("SMS_PROVIDER", "mock").lower()
    if provider_type == "aliyun":
        return AliyunSMSProvider()
    return MockSMSProvider()
