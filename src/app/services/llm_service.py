import logging

import httpx

logger = logging.getLogger(__name__)

GLM_API_KEY = "b47777cc5e654fbf96265be8c5398097.lDBejVEPN5RGMlHu"
GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


async def generate_smart_message(
    trip_destination: str, scene: str, prompt_override: str = None
) -> str:
    """
    Use GLM API to generate a personalized SMS message.
    """
    if prompt_override:
        prompt = prompt_override
    else:
        prompt = (
            f"你是一个专业的旅行社管家。请为前往【{trip_destination}】的游客写一段关于【{scene}】的短信通知。"
            "要求语气热情、专业、贴心，字数在80字以内。"
            "直接输出短信正文内容，不要带有任何解释说明、问候语或前缀（例如'尊敬的游客'，系统会自动添加）。"
        )

    headers = {"Authorization": f"Bearer {GLM_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}]}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(GLM_API_URL, json=payload, headers=headers, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"GLM LLM generation failed for {trip_destination} ({scene}): {e}")
            if "天气" in scene:
                return f"近期【{trip_destination}】天气多变，请您出行带好雨具及保暖衣物，司导会全程为您保驾护航。"
            elif "结束" in scene or "满意度" in scene:
                return f"您的【{trip_destination}】行程已圆满结束，感谢您的信任！期待您的评价反馈，祝您生活愉快！"
            return (
                f"您的【{trip_destination}】行程即将开始，请做好行前准备。如有问题请随时联系我们。"
            )
