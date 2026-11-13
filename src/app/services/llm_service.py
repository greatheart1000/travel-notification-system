from __future__ import annotations

import importlib
import logging
import os
import re

logger = logging.getLogger(__name__)

GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


def _fallback_message(trip_destination: str, scene: str) -> str:
    if "天气" in scene:
        return (
            f"近期{trip_destination}天气有变化，请带好雨具和保暖衣物。"
            "司导会根据路况调整行程，集合时间以群内通知为准。"
        )
    if "结束" in scene or "满意度" in scene:
        return (
            f"您的{trip_destination}行程已结束。感谢信任，"
            "欢迎在群里留下评价和建议，我们会逐条记录。"
        )
    return (
        f"您的{trip_destination}行程即将开始，请确认证件、航班或车次和集合时间。"
        "如有问题请联系旅行管家。"
    )


async def _call_glm(prompt: str, api_key: str) -> str | None:
    """Return generated text, or None when the provider is unavailable."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": os.getenv("GLM_MODEL", "glm-4-flash"),
        "messages": [{"role": "user", "content": prompt}],
    }
    httpx = importlib.import_module("httpx")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                GLM_API_URL, json=payload, headers=headers, timeout=15.0
            )
            response.raise_for_status()
            data = response.json()
            content = str(data["choices"][0]["message"]["content"] or "").strip()
            return content or None
        except Exception as exc:  # pragma: no cover - network/provider fallback
            logger.error("GLM request failed: %s", exc)
            return None


async def generate_smart_message(
    trip_destination: str, scene: str, prompt_override: str | None = None
) -> str:
    """Generate a smart travel message through GLM when configured, otherwise fallback."""
    api_key = os.getenv("GLM_API_KEY", "").strip()
    if not api_key:
        return _fallback_message(trip_destination, scene)

    if prompt_override:
        prompt = prompt_override
    else:
        prompt = (
            f"你是一个专业的旅行社管家。请为前往【{trip_destination}】的游客写一段关于【{scene}】的短信通知。"
            "要求语气热情、专业、贴心，字数在80字以内。"
            "直接输出短信正文内容，不要带有任何解释说明、问候语或前缀（例如'尊敬的游客'，系统会自动添加）。"
        )
    generated = await _call_glm(prompt, api_key)
    return generated or _fallback_message(trip_destination, scene)


def _local_polish(content: str, destination: str = "") -> str:
    """Deterministic polish used when no LLM key is configured.

    It keeps every fact from the source and only improves structure, tone and
    punctuation, so the result is always safe to send without review.
    """
    text = str(content or "").strip()
    if not text:
        return _fallback_message(destination or "行程", "行程提醒")

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    replacements = {
        "请知悉": "请留意",
        "特此通知": "感谢配合",
        "请务必": "请",
        "务必": "请",
        "广大游客": "各位团友",
        "尊敬的游客": "各位团友",
        "!!": "。",
        "!": "。",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"([，。！？；])\1+", r"\1", text)
    if not text.endswith(("。", "？", "；")):
        text = f"{text}。"
    return text


async def polish_travel_message(
    content: str,
    destination: str = "",
    scene: str = "行程提醒",
) -> tuple[str, str]:
    """Polish an existing notice without inventing facts.

    Returns ``(content, provider)`` where provider is ``glm`` or ``local``.
    """
    source = str(content or "").strip()
    api_key = os.getenv("GLM_API_KEY", "").strip()
    if not source:
        return _fallback_message(destination or "行程", scene), "local"
    if not api_key:
        return _local_polish(source, destination), "local"

    prompt = (
        "你是旅行社的资深行程管家。请润色下面这条准备发到企业微信游客群的中文通知。"
        "要求：1. 保留原文全部事实（时间、地点、人数、数字、集合信息），不得编造；"
        "2. 语气温暖、专业、口语化，像管家在群里说话，去掉模板腔和 AI 感；"
        "3. 可以用短句和换行，不要使用 Markdown、标题或解释；"
        "4. 保留原文中的 {{变量}} 占位符原样，不得删除或改写；"
        "5. 只输出润色后的正文，长度不超过原文的 1.5 倍。\n"
        f"目的地：{destination or '未指定'}\n"
        f"场景：{scene}\n"
        f"原文：\n{source}"
    )
    generated = await _call_glm(prompt, api_key)
    if generated:
        return generated, "glm"
    return _local_polish(source, destination), "local"
