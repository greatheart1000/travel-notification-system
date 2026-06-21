"""企业微信 API — 建群、拉人、获取 token."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
import urllib.request

logger = logging.getLogger(__name__)

WECOM_CORP_ID = os.getenv("WECOM_CORP_ID", "")
WECOM_CORP_SECRET = os.getenv("WECOM_CORP_SECRET", "")
WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"

# 内存缓存 access_token (2小时有效)
_token_cache: dict[str, Any] = {"token": "", "expires_at": 0}


def _get_access_token() -> str:
    """获取企业微信 access_token（带缓存）。"""
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"]

    if not WECOM_CORP_ID or not WECOM_CORP_SECRET:
        raise RuntimeError("WECOM_CORP_ID 和 WECOM_CORP_SECRET 未配置")

    url = f"{WECOM_API_BASE}/gettoken?corpid={WECOM_CORP_ID}&corpsecret={WECOM_CORP_SECRET}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    if data.get("errcode") != 0:
        raise RuntimeError(f"获取 access_token 失败: {data.get('errmsg')}")

    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 7200)
    logger.info("[WeComAPI] access_token 已刷新")
    return _token_cache["token"]


def _post(path: str, body: dict) -> dict:
    """通用 POST 请求到企业微信 API。"""
    token = _get_access_token()
    url = f"{WECOM_API_BASE}/{path}?access_token={token}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode())
    if result.get("errcode") != 0:
        raise RuntimeError(f"企业微信 API 错误: {result.get('errmsg')} (errcode={result.get('errcode')})")
    return result


def create_group(name: str, user_ids: list[str], owner_user_id: str = "") -> dict:
    """创建企业微信群聊。

    Args:
        name: 群聊名称（如"伊犁草原深度游-服务群"）
        user_ids: 初始成员 userid 列表（不含创建者），最多 1999 人
        owner_user_id: 群主 userid，不填则为调用者
    Returns:
        {"chatid": "ww123456", ...}
    """
    body = {"name": name, "userlist": user_ids[:1999]}
    if owner_user_id:
        body["owner"] = owner_user_id
    result = _post("appchat/create", body)
    logger.info("[WeComAPI] 群已创建: chatid=%s name=%s", result.get("chatid"), name)
    return result


def update_group(chat_id: str, name: str = "", add_users: list[str] | None = None, del_users: list[str] | None = None) -> dict:
    """修改群聊（改名/加人/踢人）。"""
    body: dict[str, Any] = {"chatid": chat_id}
    if name:
        body["name"] = name
    if add_users:
        body["add_user_list"] = add_users
    if del_users:
        body["del_user_list"] = del_users
    result = _post("appchat/update", body)
    logger.info("[WeComAPI] 群已更新: chatid=%s", chat_id)
    return result


def get_group(chat_id: str) -> dict:
    """获取群聊详情。"""
    token = _get_access_token()
    url = f"{WECOM_API_BASE}/appchat/get?access_token={token}&chatid={chat_id}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode())
    if result.get("errcode") != 0:
        raise RuntimeError(f"获取群信息失败: {result.get('errmsg')}")
    return result


def send_group_message(chat_id: str, content: str) -> dict:
    """通过应用发送群消息（需应用有群聊权限）。"""
    body = {"chatid": chat_id, "msgtype": "text", "text": {"content": content}}
    return _post("appchat/send", body)
